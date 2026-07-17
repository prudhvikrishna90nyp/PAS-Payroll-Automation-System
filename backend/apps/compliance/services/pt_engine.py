"""Professional Tax calculation engine (Sprint 9.3).

Flow
----
Payroll Result → resolve PT work-state from ``EmployeePTProfile``
(prefer profile; company/branch address is NOT used as silent fallback —
missing state is flagged for the missing-work-state report) →
load effective ``ProfessionalTaxRuleSet`` + DB slabs →
applicability / exemption → PT wages → match slab →
normal or special-month amount → immutable ``PayrollPTResult`` + component.

Historical payroll uses snapshotted ``PayrollPTResult`` values; the engine
never hardcodes AP (or any state) slab amounts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.compliance.models import (
    EmployeePTProfile,
    ProfessionalTaxRuleSet,
    ProfessionalTaxSlab,
    PTExemptionType,
)
from apps.compliance.services.pt_rules import get_pt_rule_for_state_and_date


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class PTCalculationResult:
    applicable: bool
    rule_set: ProfessionalTaxRuleSet | None
    state_code: str
    pt_wages: Decimal = ZERO
    tax_amount: Decimal = ZERO
    exemption_reason: str = ''
    missing_work_state: bool = False
    special_month_applied: bool = False
    slab_id: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def rule_set_id(self) -> int | None:
        return self.rule_set.pk if self.rule_set is not None else None

    def to_snapshot_dict(self) -> dict[str, Any]:
        data = {
            'applicable': self.applicable,
            'state_code': self.state_code,
            'pt_wages': str(self.pt_wages),
            'tax_amount': str(self.tax_amount),
            'exemption_reason': self.exemption_reason,
            'missing_work_state': self.missing_work_state,
            'special_month_applied': self.special_month_applied,
            'slab_id': self.slab_id,
            'rule_set_id': self.rule_set_id,
            'rule_name': self.rule_set.name if self.rule_set else '',
            'rule_state': self.rule_set.state_code if self.rule_set else '',
            'special_month': self.rule_set.special_month if self.rule_set else None,
        }
        data.update(self.detail)
        return data


def resolve_pt_profile(employee) -> EmployeePTProfile | None:
    try:
        return employee.pt_profile
    except ObjectDoesNotExist:
        return None
    except AttributeError:
        return None


def resolve_pt_state_code(
    employee,
    *,
    period_end: date | None = None,
    allow_company_fallback: bool = False,
) -> tuple[str, str]:
    """Return ``(state_code, source)``.

    Preferred source: ``EmployeePTProfile.state_code`` (work / PT jurisdiction).

    Company or branch registered address is **not** used unless
    ``allow_company_fallback=True`` (documented escape hatch for migration).
    Default behaviour flags missing profile/state for reports.
    """
    profile = resolve_pt_profile(employee)
    if profile is not None:
        if period_end is not None:
            if profile.effective_from and profile.effective_from > period_end:
                return '', 'profile_not_yet_effective'
            if profile.effective_to and profile.effective_to < period_end:
                return '', 'profile_expired'
        code = (profile.state_code or '').strip().upper()
        if code:
            return code, 'employee_pt_profile'
        return '', 'profile_missing_state'

    if allow_company_fallback:
        branch = getattr(employee, 'branch', None)
        if branch is not None:
            branch_state = (getattr(branch, 'state', '') or '').strip()
            if branch_state:
                # Map common full names lightly; prefer ISO-like codes already stored.
                return _normalise_state_token(branch_state), 'branch_fallback'
        company = getattr(employee, 'company', None)
        if company is not None:
            company_state = (getattr(company, 'state', '') or '').strip()
            if company_state:
                return _normalise_state_token(company_state), 'company_fallback'
    return '', 'missing_pt_profile'


def _normalise_state_token(value: str) -> str:
    """Map common full state names to short codes; pass through short codes."""
    token = value.strip().upper()
    aliases = {
        'ANDHRA PRADESH': 'AP',
        'AP': 'AP',
        'TELANGANA': 'TS',
        'TS': 'TS',
        'KARNATAKA': 'KA',
        'KA': 'KA',
        'TAMIL NADU': 'TN',
        'TN': 'TN',
        'MAHARASHTRA': 'MH',
        'MH': 'MH',
    }
    return aliases.get(token, token[:10])


def is_pt_profile_applicable(
    employee,
    *,
    period_start: date,
    period_end: date,
) -> tuple[bool, str]:
    """Base applicability before wage / slab matching."""
    profile = resolve_pt_profile(employee)

    if profile is None:
        # No profile → treat as gap (missing work state), not auto-applicable.
        return False, 'missing_pt_profile'

    if not profile.is_applicable:
        reason = profile.exemption_reason or profile.exemption_type or 'profile_not_applicable'
        return False, reason if reason else 'profile_not_applicable'

    if profile.exemption_type and profile.exemption_type != PTExemptionType.NONE:
        reason = profile.exemption_reason or profile.exemption_type
        return False, reason

    if profile.effective_from and profile.effective_from > period_end:
        return False, 'profile_not_yet_effective'
    if profile.effective_to and profile.effective_to < period_start:
        return False, 'profile_expired'

    join = getattr(employee, 'date_of_joining', None)
    exit_d = getattr(employee, 'date_of_exit', None)
    if join and join > period_end:
        return False, 'joined_after_period'
    if exit_d and exit_d < period_start:
        return False, 'exited_before_period'

    return True, 'enrolment_ok'


def determine_pt_wages_from_components(earning_rows: list[dict]) -> Decimal:
    """Sum prorated earnings flagged ``pt_applicable``.

    Fallback when no flags are present: all earning amounts (gross-like).
    """
    flagged = [row for row in earning_rows if row.get('pt_applicable')]
    if flagged:
        return _q(sum((Decimal(r['amount']) for r in flagged), ZERO))
    if not earning_rows:
        return ZERO
    return _q(sum((Decimal(r['amount']) for r in earning_rows), ZERO))


def match_slab(rule_set: ProfessionalTaxRuleSet, wages: Decimal) -> ProfessionalTaxSlab | None:
    """Load slabs from DB and return the matching band (never hardcode amounts)."""
    slabs = list(
        ProfessionalTaxSlab.objects
        .filter(rule_set=rule_set)
        .order_by('sequence', 'salary_from')
    )
    for slab in slabs:
        if slab.matches(wages):
            return slab
    return None


def calculate_pt(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set: ProfessionalTaxRuleSet | None = None,
    as_of: date | None = None,
    allow_company_fallback: bool = False,
) -> PTCalculationResult:
    """Calculate Professional Tax for one employee in a payroll period."""
    period_start = period.start_date
    period_end = period.end_date
    as_of = as_of or period_end
    payroll_month = as_of.month

    applicable, reason = is_pt_profile_applicable(
        employee, period_start=period_start, period_end=period_end
    )

    state_code, state_source = resolve_pt_state_code(
        employee,
        period_end=period_end,
        allow_company_fallback=allow_company_fallback,
    )
    missing_state = not bool(state_code)

    if not applicable:
        return PTCalculationResult(
            applicable=False,
            rule_set=rule_set,
            state_code=state_code,
            exemption_reason=reason,
            missing_work_state=missing_state or reason in {
                'missing_pt_profile',
                'profile_missing_state',
            },
            detail={
                'reason': reason,
                'state_source': state_source,
            },
        )

    if missing_state:
        return PTCalculationResult(
            applicable=False,
            rule_set=None,
            state_code='',
            exemption_reason='missing_work_state',
            missing_work_state=True,
            detail={
                'reason': 'missing_work_state',
                'state_source': state_source,
                'note': (
                    'PT jurisdiction must come from EmployeePTProfile.state_code '
                    '(work state). Company registered address alone is insufficient.'
                ),
            },
        )

    if rule_set is None:
        try:
            rule_set = get_pt_rule_for_state_and_date(state_code, as_of)
        except ValidationError as exc:
            return PTCalculationResult(
                applicable=False,
                rule_set=None,
                state_code=state_code,
                exemption_reason='no_rule_set',
                detail={
                    'reason': 'no_rule_set',
                    'state_source': state_source,
                    'error': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
                },
            )
    elif rule_set.state_code.upper() != state_code:
        # Per-employee state wins; ignore mismatched run-level snapshot.
        try:
            rule_set = get_pt_rule_for_state_and_date(state_code, as_of)
        except ValidationError as exc:
            return PTCalculationResult(
                applicable=False,
                rule_set=None,
                state_code=state_code,
                exemption_reason='no_rule_set',
                detail={
                    'reason': 'no_rule_set',
                    'state_source': state_source,
                    'error': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
                },
            )

    pt_wages = determine_pt_wages_from_components(earning_rows)
    slab = match_slab(rule_set, pt_wages)
    if slab is None:
        return PTCalculationResult(
            applicable=True,
            rule_set=rule_set,
            state_code=state_code,
            pt_wages=pt_wages,
            tax_amount=ZERO,
            exemption_reason='no_matching_slab',
            detail={
                'reason': 'no_matching_slab',
                'state_source': state_source,
                'payroll_month': payroll_month,
            },
        )

    special = rule_set.special_month
    special_applied = bool(special and payroll_month == special)
    tax = _q(slab.amount_for_month(month=payroll_month, special_month=special))

    return PTCalculationResult(
        applicable=True,
        rule_set=rule_set,
        state_code=state_code,
        pt_wages=pt_wages,
        tax_amount=tax,
        exemption_reason='',
        missing_work_state=False,
        special_month_applied=special_applied,
        slab_id=slab.pk,
        detail={
            'reason': 'special_month' if special_applied else 'normal_month',
            'state_source': state_source,
            'payroll_month': payroll_month,
            'special_month': special,
            'salary_from': str(slab.salary_from),
            'salary_to': str(slab.salary_to) if slab.salary_to is not None else None,
            'tax_amount_normal': str(slab.tax_amount),
            'tax_amount_special': (
                str(slab.special_month_tax_amount)
                if slab.special_month_tax_amount is not None
                else None
            ),
            'frequency': rule_set.frequency,
            'slab_sequence': slab.sequence,
        },
    )


def build_pt_component_rows(pt: PTCalculationResult) -> list[dict]:
    """PayrollResultComponent row for employee Professional Tax."""
    from apps.payroll.models import ComponentType

    snapshot = pt.to_snapshot_dict()
    return [
        {
            'component_code': 'STAT_PT',
            'component_name': 'Professional Tax',
            'component_type': ComponentType.DEDUCTION,
            'amount': pt.tax_amount if pt.applicable else ZERO,
            'calculation_detail': {**snapshot, 'kind': 'employee_pt'},
        },
    ]
