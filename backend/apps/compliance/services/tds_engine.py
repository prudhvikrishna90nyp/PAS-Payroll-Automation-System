"""TDS / income-tax calculation engine (Sprint 9.4).

Flow
----
Payroll Result → EmployeeTaxProfile → regime (declaration / profile, with
regime-change deadline) → FY tax rules (DB) → project annual income
(YTD + remaining months + previous employer) → exemptions/deductions
(old-regime declarations; new-regime std deduction) → taxable income →
slabs → rebate / surcharge / cess → subtract previous TDS → remaining
liability / months left → monthly_tds → immutable PayrollTDSResult + component.

Rates and slabs are NEVER hardcoded — always loaded from
``FinancialYearTaxRule`` / ``TaxSlab``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.compliance.models import (
    EmployeeTaxProfile,
    FinancialYearTaxRule,
    TaxDeclaration,
    TaxDeclarationStatus,
    TaxRegime,
    TaxSlab,
)
from apps.compliance.services.tds_projection import IncomeProjection, project_annual_income
from apps.compliance.services.tds_rules import (
    financial_year_for_date,
    get_tax_rule_for_fy_regime_and_date,
    regime_change_deadline,
)


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def _q(amount: Decimal | int | str | None) -> Decimal:
    if amount is None:
        return ZERO
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class TDSCalculationResult:
    applicable: bool
    rule_set: FinancialYearTaxRule | None
    financial_year: str = ''
    tax_regime: str = ''
    taxable_salary: Decimal = ZERO
    tax_before_rebate: Decimal = ZERO
    rebate: Decimal = ZERO
    tax_after_rebate: Decimal = ZERO
    surcharge: Decimal = ZERO
    cess: Decimal = ZERO
    relief: Decimal = ZERO
    annual_tax: Decimal = ZERO
    previous_tds: Decimal = ZERO
    remaining_liability: Decimal = ZERO
    months_left: int = 1
    monthly_tds: Decimal = ZERO
    projection: IncomeProjection | None = None
    exemption_reason: str = ''
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def rule_set_id(self) -> int | None:
        return self.rule_set.pk if self.rule_set is not None else None

    def to_snapshot_dict(self) -> dict[str, Any]:
        data = {
            'applicable': self.applicable,
            'financial_year': self.financial_year,
            'tax_regime': self.tax_regime,
            'taxable_salary': str(self.taxable_salary),
            'tax_before_rebate': str(self.tax_before_rebate),
            'rebate': str(self.rebate),
            'tax_after_rebate': str(self.tax_after_rebate),
            'surcharge': str(self.surcharge),
            'cess': str(self.cess),
            'relief': str(self.relief),
            'annual_tax': str(self.annual_tax),
            'previous_tds': str(self.previous_tds),
            'remaining_liability': str(self.remaining_liability),
            'months_left': self.months_left,
            'monthly_tds': str(self.monthly_tds),
            'exemption_reason': self.exemption_reason,
            'rule_set_id': self.rule_set_id,
            'rule_code': self.rule_set.code if self.rule_set else '',
            'cess_rate': str(self.rule_set.cess_rate) if self.rule_set else '',
            'rebate_limit': str(self.rule_set.rebate_limit) if self.rule_set else '',
            'standard_deduction': (
                str(self.rule_set.standard_deduction) if self.rule_set else ''
            ),
        }
        if self.projection is not None:
            data['projection'] = self.projection.to_dict()
            data['current_month_taxable'] = str(self.projection.current_month_taxable)
        data.update(self.detail)
        return data


def resolve_tax_profile(employee) -> EmployeeTaxProfile | None:
    try:
        return employee.tax_profile
    except ObjectDoesNotExist:
        return None
    except AttributeError:
        return None


def resolve_regime(
    employee,
    *,
    financial_year: str,
    as_of: date,
) -> tuple[str, str]:
    """Return ``(regime, source)`` honouring the 31 July regime-change deadline.

    Documented rule
    ---------------
    Employees may change tax regime for a financial year until **31 July** of
    that FY (e.g. FY 2024-25 → 2024-07-31). Priority:
      1. Approved/submitted ``TaxDeclaration.regime`` for the FY
      2. ``EmployeeTaxProfile.default_tax_regime``
      3. Default NEW

    After the deadline, if a declaration exists it is used; otherwise the
    profile default effective at the deadline date is used (no late flips
    via profile alone after deadline without an approved declaration).
    """
    deadline = regime_change_deadline(financial_year)
    decl = (
        TaxDeclaration.objects
        .filter(employee=employee, financial_year=financial_year)
        .order_by('-updated_at')
        .first()
    )
    profile = resolve_tax_profile(employee)
    profile_regime = (
        profile.default_tax_regime if profile is not None else TaxRegime.NEW
    )

    if decl is not None and decl.status in {
        TaxDeclarationStatus.APPROVED,
        TaxDeclarationStatus.SUBMITTED,
    }:
        # Declaration always wins once submitted/approved for the FY.
        return decl.regime, 'tax_declaration'

    if as_of > deadline:
        # After deadline without declaration: freeze to profile default.
        return profile_regime, 'profile_after_deadline'

    return profile_regime, 'employee_tax_profile'


def load_slabs(rule: FinancialYearTaxRule) -> list[TaxSlab]:
    return list(
        TaxSlab.objects.filter(rule=rule).order_by('sequence', 'income_from')
    )


def compute_slab_tax(taxable_income: Decimal, slabs: list[TaxSlab]) -> Decimal:
    """Progressive tax from DB slabs (Decimal only — no eval).

    Seed slabs use inclusive bounds with ``income_from`` of the next band at
    prior ``income_to + 0.01`` (e.g. 0–250000, then 250000.01–500000).
    """
    income = _q(taxable_income)
    if income <= 0:
        return ZERO
    tax = ZERO
    for slab in slabs:
        low = Decimal(slab.income_from)
        high = Decimal(slab.income_to) if slab.income_to is not None else income
        rate = Decimal(slab.rate)
        if income < low or rate == 0:
            continue
        upper = min(income, high)
        if upper < low:
            continue
        if low == 0:
            portion = upper - low
        else:
            prev_end = low - Decimal('0.01')
            portion = upper - prev_end
        if portion > 0:
            tax += portion * rate
    return _q(tax)


def apply_rebate(
    tax: Decimal,
    *,
    taxable_income: Decimal,
    rebate_limit: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return (rebate, tax_after_rebate). Full rebate when income ≤ limit."""
    if taxable_income <= rebate_limit and rebate_limit > 0:
        rebate = _q(tax)
        return rebate, ZERO
    return ZERO, _q(tax)


def apply_surcharge(
    tax_after_rebate: Decimal,
    taxable_income: Decimal,
    surcharge_rules: list | None,
) -> Decimal:
    """Apply matching surcharge band from rule JSON (DB-sourced)."""
    if not surcharge_rules or tax_after_rebate <= 0:
        return ZERO
    income = _q(taxable_income)
    for band in surcharge_rules:
        low = _q(band.get('income_from', 0))
        high_raw = band.get('income_to')
        high = _q(high_raw) if high_raw is not None else None
        rate = Decimal(str(band.get('rate', '0')))
        if income < low:
            continue
        if high is not None and income > high:
            continue
        return _q(tax_after_rebate * rate)
    return ZERO


def calculate_tds_for_employee(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set: FinancialYearTaxRule | None = None,
    as_of: date | None = None,
    exclude_run_id: int | None = None,
) -> TDSCalculationResult:
    """Calculate monthly TDS for one employee in a payroll period."""
    as_of = as_of or period.end_date
    fy = financial_year_for_date(as_of)
    profile = resolve_tax_profile(employee)

    if profile is not None and not profile.is_tds_applicable:
        return TDSCalculationResult(
            applicable=False,
            rule_set=rule_set,
            financial_year=fy,
            exemption_reason='profile_not_applicable',
            detail={'reason': 'profile_not_applicable'},
        )

    join = getattr(employee, 'date_of_joining', None)
    exit_d = getattr(employee, 'date_of_exit', None)
    if join and join > period.end_date:
        return TDSCalculationResult(
            applicable=False,
            rule_set=rule_set,
            financial_year=fy,
            exemption_reason='joined_after_period',
        )
    if exit_d and exit_d < period.start_date:
        return TDSCalculationResult(
            applicable=False,
            rule_set=rule_set,
            financial_year=fy,
            exemption_reason='exited_before_period',
        )

    regime, regime_source = resolve_regime(employee, financial_year=fy, as_of=as_of)

    if rule_set is None:
        try:
            rule_set = get_tax_rule_for_fy_regime_and_date(fy, regime, as_of)
        except ValidationError as exc:
            return TDSCalculationResult(
                applicable=False,
                rule_set=None,
                financial_year=fy,
                tax_regime=regime,
                exemption_reason='no_rule_set',
                detail={
                    'reason': 'no_rule_set',
                    'regime_source': regime_source,
                    'error': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
                },
            )
    elif rule_set.tax_regime != regime or rule_set.financial_year != fy:
        try:
            rule_set = get_tax_rule_for_fy_regime_and_date(fy, regime, as_of)
        except ValidationError as exc:
            return TDSCalculationResult(
                applicable=False,
                rule_set=None,
                financial_year=fy,
                tax_regime=regime,
                exemption_reason='no_rule_set',
                detail={
                    'reason': 'no_rule_set',
                    'regime_source': regime_source,
                    'error': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
                },
            )

    projection = project_annual_income(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule=rule_set,
        regime=regime,
        exclude_run_id=exclude_run_id,
    )

    slabs = load_slabs(rule_set)
    tax_before = compute_slab_tax(projection.taxable_income, slabs)
    rebate, tax_after = apply_rebate(
        tax_before,
        taxable_income=projection.taxable_income,
        rebate_limit=Decimal(rule_set.rebate_limit),
    )
    surcharge = apply_surcharge(
        tax_after,
        projection.taxable_income,
        rule_set.surcharge_rules,
    )
    cess_base = tax_after + surcharge
    cess = _q(cess_base * Decimal(rule_set.cess_rate))
    relief = ZERO
    annual_tax = _q(cess_base + cess - relief)
    previous_tds = _q(projection.ytd_payroll_tds + projection.previous_employer_tds)
    remaining = max(ZERO, _q(annual_tax - previous_tds))
    months_left = max(1, projection.remaining_months_including_current)
    monthly = _q(remaining / Decimal(months_left))

    return TDSCalculationResult(
        applicable=True,
        rule_set=rule_set,
        financial_year=fy,
        tax_regime=regime,
        taxable_salary=projection.taxable_income,
        tax_before_rebate=tax_before,
        rebate=rebate,
        tax_after_rebate=tax_after,
        surcharge=surcharge,
        cess=cess,
        relief=relief,
        annual_tax=annual_tax,
        previous_tds=previous_tds,
        remaining_liability=remaining,
        months_left=months_left,
        monthly_tds=monthly,
        projection=projection,
        detail={
            'regime_source': regime_source,
            'regime_change_deadline': str(regime_change_deadline(fy)),
            'slab_count': len(slabs),
            'surcharge_rate_applied': (
                str(_q(surcharge / tax_after)) if tax_after > 0 and surcharge > 0 else '0'
            ),
        },
    )


# Public alias matching statutory naming.
calculate_tds = calculate_tds_for_employee


def build_tds_component_rows(tds: TDSCalculationResult) -> list[dict]:
    """PayrollResultComponent row for employee TDS."""
    from apps.payroll.models import ComponentType

    snapshot = tds.to_snapshot_dict()
    return [
        {
            'component_code': 'STAT_TDS',
            'component_name': 'TDS',
            'component_type': ComponentType.DEDUCTION,
            'amount': tds.monthly_tds if tds.applicable else ZERO,
            'calculation_detail': {**snapshot, 'kind': 'employee_tds'},
        },
    ]
