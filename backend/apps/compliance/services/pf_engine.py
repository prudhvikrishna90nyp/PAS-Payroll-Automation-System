"""EPF calculation engine (Sprint 9.1).

Flow
----
Payroll earning rows → eligibility → actual PF wages → ceiling →
EE PF (+ VPF) → ER PF → EPS split → employer EPF → EDLI / admin / inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from apps.compliance.models import EmployeePFProfile, PFRuleSet
from apps.compliance.services.pf_rules import get_pf_rule_for_date


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class PFCalculationResult:
    eligible: bool
    rule_set: PFRuleSet | None
    rule_version: str
    actual_pf_wages: Decimal = ZERO
    pf_wages: Decimal = ZERO
    employee_pf: Decimal = ZERO
    voluntary_pf: Decimal = ZERO
    employer_pf: Decimal = ZERO
    eps: Decimal = ZERO
    epf: Decimal = ZERO
    edli: Decimal = ZERO
    admin_charge: Decimal = ZERO
    inspection_charge: Decimal = ZERO
    ncp_days: Decimal = ZERO
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def total_employee_deduction(self) -> Decimal:
        """Amount deducted from employee net (EE PF + VPF)."""
        return _q(self.employee_pf + self.voluntary_pf)

    def to_detail_dict(self) -> dict[str, Any]:
        data = {
            'eligible': self.eligible,
            'rule_version': self.rule_version,
            'actual_pf_wages': str(self.actual_pf_wages),
            'pf_wages': str(self.pf_wages),
            'employee_pf': str(self.employee_pf),
            'voluntary_pf': str(self.voluntary_pf),
            'employer_pf': str(self.employer_pf),
            'eps': str(self.eps),
            'epf': str(self.epf),
            'edli': str(self.edli),
            'admin_charge': str(self.admin_charge),
            'inspection_charge': str(self.inspection_charge),
            'ncp_days': str(self.ncp_days),
        }
        data.update(self.detail)
        return data


def resolve_pf_profile(employee) -> EmployeePFProfile | None:
    try:
        return employee.pf_profile
    except EmployeePFProfile.DoesNotExist:
        return None
    except AttributeError:
        return None


def is_pf_eligible(employee, *, period_start: date, period_end: date) -> tuple[bool, str]:
    """Return (eligible, reason). Uses EmployeePFProfile when present, else Employee.pf_eligible."""
    profile = resolve_pf_profile(employee)

    if profile is not None:
        if not profile.is_pf_applicable:
            return False, 'profile_not_applicable'
        join = profile.joining_pf_date or getattr(employee, 'date_of_joining', None)
        exit_d = profile.exit_pf_date or getattr(employee, 'date_of_exit', None)
    else:
        if not getattr(employee, 'pf_eligible', True):
            return False, 'employee_not_pf_eligible'
        join = getattr(employee, 'date_of_joining', None)
        exit_d = getattr(employee, 'date_of_exit', None)

    if join and join > period_end:
        return False, 'joined_after_period'
    if exit_d and exit_d < period_start:
        return False, 'exited_before_period'
    return True, 'eligible'


def determine_pf_wages_from_components(earning_rows: list[dict]) -> Decimal:
    """Sum prorated earnings flagged ``pf_applicable``.

    Fallback when no flags are present: BASIC + DA (case-insensitive codes).
    """
    flagged = [
        row for row in earning_rows
        if row.get('pf_applicable')
    ]
    if flagged:
        return _q(sum((Decimal(r['amount']) for r in flagged), ZERO))

    fallback_codes = {'BASIC', 'DA', 'DEARNESS', 'DEARNESSALLOWANCE'}
    total = ZERO
    for row in earning_rows:
        code = str(row.get('component_code') or '').upper().replace(' ', '').replace('_', '')
        # Normalise DEARNESS_ALLOWANCE → DEARNESSALLOWANCE already via replace
        raw = str(row.get('component_code') or '').upper()
        if raw in {'BASIC', 'DA'} or raw in fallback_codes or code in {'BASIC', 'DA', 'DEARNESSALLOWANCE'}:
            total += Decimal(row['amount'])
    return _q(total)


def apply_pf_ceiling(
    actual_pf_wages: Decimal,
    ceiling: Decimal,
    *,
    higher_pension: bool = False,
) -> Decimal:
    """PF wages used for EE/ER/EDLI.

    Higher pension opt-in uses actual PF wages (no statutory ceiling) so EPS
    and employer shares stay consistent on the same base.
    """
    if higher_pension or ceiling <= 0:
        return _q(actual_pf_wages)
    return _q(min(actual_pf_wages, ceiling))


def calculate_eps(
    *,
    actual_pf_wages: Decimal,
    pf_wages: Decimal,
    eps_rate: Decimal,
    ceiling: Decimal,
    higher_pension: bool,
) -> Decimal:
    """EPS = eps_rate × wage base; wage base is uncapped when higher_pension is True."""
    if higher_pension:
        base = actual_pf_wages
    else:
        # EPS wage is min(actual, ceiling); pf_wages already capped for standard path
        base = min(actual_pf_wages, ceiling) if ceiling > 0 else actual_pf_wages
        # Prefer explicit pf_wages when already computed
        if pf_wages is not None:
            base = pf_wages
    return _q(Decimal(base) * Decimal(eps_rate))


def calculate_pf(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set: PFRuleSet | None = None,
    ncp_days: Decimal | None = None,
    as_of: date | None = None,
) -> PFCalculationResult:
    """Calculate EPF amounts for one employee in a payroll period."""
    period_start = period.start_date
    period_end = period.end_date
    as_of = as_of or period_end

    eligible, reason = is_pf_eligible(
        employee, period_start=period_start, period_end=period_end
    )
    if not eligible:
        return PFCalculationResult(
            eligible=False,
            rule_set=rule_set,
            rule_version=getattr(rule_set, 'code', '') if rule_set else '',
            ncp_days=_q(ncp_days or ZERO),
            detail={'reason': reason},
        )

    if rule_set is None:
        rule_set = get_pf_rule_for_date(as_of)

    profile = resolve_pf_profile(employee)
    higher_pension = bool(profile and profile.higher_pension)
    voluntary_pf_flag = bool(profile and profile.voluntary_pf)
    vpf_pct = Decimal(profile.vpf_percentage) if profile and voluntary_pf_flag else ZERO

    actual = determine_pf_wages_from_components(earning_rows)
    ceiling = Decimal(rule_set.pf_wage_ceiling)
    pf_wages = apply_pf_ceiling(actual, ceiling, higher_pension=higher_pension)

    employee_pf = _q(pf_wages * Decimal(rule_set.employee_pf_rate))
    voluntary = _q(pf_wages * vpf_pct) if voluntary_pf_flag else ZERO
    employer_pf = _q(pf_wages * Decimal(rule_set.employer_pf_rate))
    eps = calculate_eps(
        actual_pf_wages=actual,
        pf_wages=pf_wages,
        eps_rate=Decimal(rule_set.eps_rate),
        ceiling=ceiling,
        higher_pension=higher_pension,
    )
    # Employer EPF share cannot go negative if EPS > employer total (edge case)
    epf = _q(max(ZERO, employer_pf - eps))
    edli_base = pf_wages  # EDLI uses capped wages
    edli = _q(edli_base * Decimal(rule_set.edli_rate))
    admin = _q(pf_wages * Decimal(rule_set.admin_charge))
    inspection = _q(pf_wages * Decimal(rule_set.inspection_charge))

    return PFCalculationResult(
        eligible=True,
        rule_set=rule_set,
        rule_version=rule_set.code,
        actual_pf_wages=actual,
        pf_wages=pf_wages,
        employee_pf=employee_pf,
        voluntary_pf=voluntary,
        employer_pf=employer_pf,
        eps=eps,
        epf=epf,
        edli=edli,
        admin_charge=admin,
        inspection_charge=inspection,
        ncp_days=_q(ncp_days or ZERO),
        detail={
            'reason': reason,
            'higher_pension': higher_pension,
            'voluntary_pf': voluntary_pf_flag,
            'vpf_percentage': str(vpf_pct),
            'ceiling': str(ceiling),
            'employee_pf_rate': str(rule_set.employee_pf_rate),
            'employer_pf_rate': str(rule_set.employer_pf_rate),
            'eps_rate': str(rule_set.eps_rate),
        },
    )


def build_pf_component_rows(pf: PFCalculationResult) -> list[dict]:
    """PayrollResultComponent rows for employee PF (+ VPF) and employer contributions."""
    from apps.payroll.models import ComponentType

    detail = pf.to_detail_dict()
    rows = [
        {
            'component_code': 'STAT_PF',
            'component_name': 'Employee Provident Fund',
            'component_type': ComponentType.DEDUCTION,
            'amount': pf.employee_pf if pf.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'employee_pf'},
        },
    ]
    if pf.eligible and pf.voluntary_pf > 0:
        rows.append({
            'component_code': 'STAT_VPF',
            'component_name': 'Voluntary Provident Fund',
            'component_type': ComponentType.DEDUCTION,
            'amount': pf.voluntary_pf,
            'calculation_detail': {**detail, 'kind': 'voluntary_pf'},
        })
    # Employer lines (informational / CTC — not employee deductions)
    rows.extend([
        {
            'component_code': 'STAT_ER_PF',
            'component_name': 'Employer PF (total)',
            'component_type': ComponentType.EMPLOYER_CONTRIBUTION,
            'amount': pf.employer_pf if pf.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'employer_pf'},
        },
        {
            'component_code': 'STAT_EPS',
            'component_name': 'Employer EPS',
            'component_type': ComponentType.EMPLOYER_CONTRIBUTION,
            'amount': pf.eps if pf.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'eps'},
        },
        {
            'component_code': 'STAT_ER_EPF',
            'component_name': 'Employer EPF',
            'component_type': ComponentType.EMPLOYER_CONTRIBUTION,
            'amount': pf.epf if pf.eligible else ZERO,
            'calculation_detail': {**detail, 'kind': 'employer_epf'},
        },
    ])
    return rows
