"""ESI calculation engine (Sprint 9.2).

Flow
----
Payroll earning rows → load effective ESI rule → employee ESI profile →
applicability + contribution-period continuity → ESI wages →
EE contrib → ER contrib → immutable PayrollESIResult (+ component lines).

Contribution-period continuity (documented)
-------------------------------------------
ESI contribution periods are 1 Apr–30 Sep and 1 Oct–31 Mar.

Once an employee is covered in a contribution period (wages at/below the
eligibility ceiling, or already marked covered), they remain covered for
the rest of that period even if wages later exceed the ceiling — unless
they have exited ESI / employment. Eligibility is NOT dropped solely
because one month crosses the wage limit mid-period.

Historical payroll uses snapshotted ``PayrollRun.esi_rule_set`` /
``PayrollESIResult`` values; the engine never hardcodes rates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from apps.compliance.models import EmployeeESIProfile, ESIRuleSet, RoundingMethod
from apps.compliance.services.esi_rules import get_esi_rule_for_date


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')
ONE = Decimal('1')


def _round_amount(amount: Decimal, method: str) -> Decimal:
    if method == RoundingMethod.NEAREST_RUPEE:
        return Decimal(amount).quantize(ONE, rounding=ROUND_HALF_UP)
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class ESICalculationResult:
    eligible: bool
    rule_set: ESIRuleSet | None
    rule_version: str
    esi_wages: Decimal = ZERO
    employee_esi: Decimal = ZERO
    employer_esi: Decimal = ZERO
    above_wage_limit: bool = False
    continuity_applied: bool = False
    daily_wage_exemption: bool = False
    missing_ip_number: bool = False
    eligibility_notes: str = ''
    detail: dict[str, Any] = field(default_factory=dict)

    def to_detail_dict(self) -> dict[str, Any]:
        data = {
            'eligible': self.eligible,
            'rule_version': self.rule_version,
            'esi_wages': str(self.esi_wages),
            'employee_esi': str(self.employee_esi),
            'employer_esi': str(self.employer_esi),
            'above_wage_limit': self.above_wage_limit,
            'continuity_applied': self.continuity_applied,
            'daily_wage_exemption': self.daily_wage_exemption,
            'missing_ip_number': self.missing_ip_number,
            'eligibility_notes': self.eligibility_notes,
        }
        data.update(self.detail)
        return data


def resolve_esi_profile(employee) -> EmployeeESIProfile | None:
    try:
        return employee.esi_profile
    except EmployeeESIProfile.DoesNotExist:
        return None
    except AttributeError:
        return None


def get_esi_contribution_period(as_of: date) -> tuple[date, date]:
    """Return (start, end) of the ESI contribution period containing ``as_of``.

    Periods: 1 Apr–30 Sep and 1 Oct–31 Mar.
    """
    if 4 <= as_of.month <= 9:
        return date(as_of.year, 4, 1), date(as_of.year, 9, 30)
    if as_of.month >= 10:
        return date(as_of.year, 10, 1), date(as_of.year + 1, 3, 31)
    return date(as_of.year - 1, 10, 1), date(as_of.year, 3, 31)


def resolve_ip_number(employee) -> str:
    profile = resolve_esi_profile(employee)
    if profile and profile.ip_number:
        return ''.join(profile.ip_number.split())
    return ''


def is_esi_profile_applicable(employee, *, period_start: date, period_end: date) -> tuple[bool, str]:
    """Base applicability (enrolment / dates) before wage-limit / continuity checks."""
    profile = resolve_esi_profile(employee)

    if profile is not None:
        if not profile.is_esi_applicable:
            return False, 'profile_not_applicable'
        join = profile.joining_esi_date or getattr(employee, 'date_of_joining', None)
        exit_d = profile.exit_esi_date or getattr(employee, 'date_of_exit', None)
    else:
        if not getattr(employee, 'esi_eligible', False):
            return False, 'employee_not_esi_eligible'
        join = getattr(employee, 'date_of_joining', None)
        exit_d = getattr(employee, 'date_of_exit', None)

    if join and join > period_end:
        return False, 'joined_after_period'
    if exit_d and exit_d < period_start:
        return False, 'exited_before_period'
    return True, 'enrolment_ok'


def determine_esi_wages_from_components(earning_rows: list[dict]) -> Decimal:
    """Sum prorated earnings flagged ``esi_applicable``.

    Fallback when no flags are present: all earning amounts (gross-like).
    """
    flagged = [row for row in earning_rows if row.get('esi_applicable')]
    if flagged:
        return _q(sum((Decimal(r['amount']) for r in flagged), ZERO))
    if not earning_rows:
        return ZERO
    return _q(sum((Decimal(r['amount']) for r in earning_rows), ZERO))


def was_covered_in_contribution_period(
    employee,
    *,
    cp_start: date,
    cp_end: date,
    period_start: date,
) -> bool:
    """True if employee is already covered in this contribution period.

    Sources (either is enough):
    1. ``EmployeeESIProfile.covered_period_start`` matches ``cp_start``
    2. A prior ``PayrollESIResult`` in the same company/contribution period
       with ``is_eligible=True`` for a payroll period ending before this one
    """
    profile = resolve_esi_profile(employee)
    if profile is not None and profile.covered_period_start == cp_start:
        return True

    from apps.compliance.models import PayrollESIResult

    prior = (
        PayrollESIResult.objects
        .filter(
            is_eligible=True,
            payroll_result__employee_id=employee.pk,
            payroll_result__run__period__end_date__gte=cp_start,
            payroll_result__run__period__end_date__lte=cp_end,
            payroll_result__run__period__end_date__lt=period_start,
        )
        .exists()
    )
    return prior


def mark_covered_in_contribution_period(employee, cp_start: date, cp_end: date) -> None:
    """Persist continuity marker on the employee ESI profile (idempotent)."""
    profile = resolve_esi_profile(employee)
    if profile is None:
        return
    if profile.covered_period_start == cp_start and profile.covered_period_end == cp_end:
        return
    profile.covered_period_start = cp_start
    profile.covered_period_end = cp_end
    profile.save(update_fields=['covered_period_start', 'covered_period_end', 'updated_at'])


def calculate_esi(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set: ESIRuleSet | None = None,
    as_of: date | None = None,
    payable_days: Decimal | None = None,
    calendar_days: Decimal | None = None,
    update_continuity: bool = True,
) -> ESICalculationResult:
    """Calculate ESI amounts for one employee in a payroll period."""
    period_start = period.start_date
    period_end = period.end_date
    as_of = as_of or period_end

    applicable, reason = is_esi_profile_applicable(
        employee, period_start=period_start, period_end=period_end
    )
    if not applicable:
        return ESICalculationResult(
            eligible=False,
            rule_set=rule_set,
            rule_version=getattr(rule_set, 'code', '') if rule_set else '',
            eligibility_notes=reason,
            detail={'reason': reason},
        )

    if rule_set is None:
        rule_set = get_esi_rule_for_date(as_of)

    rounding = rule_set.rounding_method or RoundingMethod.HALF_UP
    esi_wages = determine_esi_wages_from_components(earning_rows)
    wage_limit = Decimal(rule_set.eligibility_wage_limit)
    above_limit = esi_wages > wage_limit

    cp_start, cp_end = get_esi_contribution_period(period_end)
    continuity = False
    if above_limit:
        continuity = was_covered_in_contribution_period(
            employee,
            cp_start=cp_start,
            cp_end=cp_end,
            period_start=period_start,
        )
        if not continuity:
            ip = resolve_ip_number(employee)
            return ESICalculationResult(
                eligible=False,
                rule_set=rule_set,
                rule_version=rule_set.code,
                esi_wages=esi_wages,
                above_wage_limit=True,
                continuity_applied=False,
                missing_ip_number=not bool(ip),
                eligibility_notes='above_wage_limit_no_continuity',
                detail={
                    'reason': 'above_wage_limit_no_continuity',
                    'wage_limit': str(wage_limit),
                    'contribution_period_start': cp_start.isoformat(),
                    'contribution_period_end': cp_end.isoformat(),
                    'employee_rate': str(rule_set.employee_rate),
                    'employer_rate': str(rule_set.employer_rate),
                },
            )

    # Eligible (at/below limit, or continuity)
    ip = resolve_ip_number(employee)
    missing_ip = not bool(ip)

    # Average daily wage for exemption: ESI wages / days
    days = calendar_days
    profile = resolve_esi_profile(employee)
    if profile and profile.is_daily_wage_worker and payable_days is not None and payable_days > 0:
        days = payable_days
    if days is None or days <= 0:
        days = Decimal((period_end - period_start).days + 1)
    avg_daily = _q(esi_wages / days) if days > 0 else ZERO
    exemption_limit = Decimal(rule_set.daily_wage_exemption_limit)
    daily_exempt = avg_daily <= exemption_limit and esi_wages > 0

    if esi_wages <= 0:
        employee_esi = ZERO
        employer_esi = ZERO
        notes = 'zero_esi_wages'
    elif daily_exempt:
        employee_esi = ZERO
        employer_esi = _round_amount(esi_wages * Decimal(rule_set.employer_rate), rounding)
        notes = 'daily_wage_exemption'
    else:
        employee_esi = _round_amount(esi_wages * Decimal(rule_set.employee_rate), rounding)
        employer_esi = _round_amount(esi_wages * Decimal(rule_set.employer_rate), rounding)
        notes = 'eligible' if not continuity else 'eligible_via_continuity'

    if missing_ip:
        notes = f'{notes};missing_ip_number'

    if update_continuity and esi_wages > 0:
        mark_covered_in_contribution_period(employee, cp_start, cp_end)

    return ESICalculationResult(
        eligible=True,
        rule_set=rule_set,
        rule_version=rule_set.code,
        esi_wages=esi_wages,
        employee_esi=employee_esi,
        employer_esi=employer_esi,
        above_wage_limit=above_limit,
        continuity_applied=continuity,
        daily_wage_exemption=daily_exempt and esi_wages > 0,
        missing_ip_number=missing_ip,
        eligibility_notes=notes,
        detail={
            'reason': notes,
            'wage_limit': str(wage_limit),
            'avg_daily_wage': str(avg_daily),
            'daily_wage_exemption_limit': str(exemption_limit),
            'contribution_period_start': cp_start.isoformat(),
            'contribution_period_end': cp_end.isoformat(),
            'employee_rate': str(rule_set.employee_rate),
            'employer_rate': str(rule_set.employer_rate),
            'rounding_method': rounding,
            'ip_number_present': not missing_ip,
        },
    )


def build_esi_component_rows(esi: ESICalculationResult) -> list[dict]:
    """PayrollResultComponent rows for employee ESI and employer ESI."""
    from apps.payroll.models import ComponentType

    detail = esi.to_detail_dict()
    return [
        {
            'component_code': 'STAT_ESI',
            'component_name': 'Employee State Insurance',
            'component_type': ComponentType.DEDUCTION,
            'amount': esi.employee_esi if esi.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'employee_esi'},
        },
        {
            'component_code': 'STAT_ER_ESI',
            'component_name': 'Employer ESI',
            'component_type': ComponentType.EMPLOYER_CONTRIBUTION,
            'amount': esi.employer_esi if esi.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'employer_esi'},
        },
    ]
