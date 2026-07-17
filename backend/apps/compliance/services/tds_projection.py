"""Annual income / TDS projection helpers (Sprint 9.4).

Projection basis (preserved in calculation snapshots):
  projected_gross = YTD taxable (prior months in FY, excl. current)
                    + current month taxable
                    + remaining_months_after_current × current month taxable
                    + previous employer taxable income

Months remaining for TDS recovery include the current month.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Sum

from apps.compliance.models import (
    PreviousEmployerIncome,
    TaxDeclaration,
    TaxDeclarationStatus,
    TaxRegime,
)
from apps.compliance.services.tds_rules import (
    financial_year_for_date,
    fy_date_bounds,
    remaining_months_in_fy,
)


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def _q(amount: Decimal | int | str | None) -> Decimal:
    if amount is None:
        return ZERO
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class IncomeProjection:
    financial_year: str
    ytd_taxable: Decimal = ZERO
    current_month_taxable: Decimal = ZERO
    remaining_months_including_current: int = 1
    projected_future_months: Decimal = ZERO
    previous_employer_income: Decimal = ZERO
    previous_employer_tds: Decimal = ZERO
    ytd_payroll_tds: Decimal = ZERO
    projected_annual_income: Decimal = ZERO
    standard_deduction: Decimal = ZERO
    old_regime_deductions: Decimal = ZERO
    taxable_income: Decimal = ZERO
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            'financial_year': self.financial_year,
            'ytd_taxable': str(self.ytd_taxable),
            'current_month_taxable': str(self.current_month_taxable),
            'remaining_months_including_current': self.remaining_months_including_current,
            'projected_future_months': str(self.projected_future_months),
            'previous_employer_income': str(self.previous_employer_income),
            'previous_employer_tds': str(self.previous_employer_tds),
            'ytd_payroll_tds': str(self.ytd_payroll_tds),
            'projected_annual_income': str(self.projected_annual_income),
            'standard_deduction': str(self.standard_deduction),
            'old_regime_deductions': str(self.old_regime_deductions),
            'taxable_income': str(self.taxable_income),
        }
        data.update(self.detail)
        return data


def determine_taxable_salary_from_components(earning_rows: list[dict]) -> Decimal:
    """Sum prorated earnings flagged ``tds_applicable``, else all earnings."""
    flagged = [row for row in earning_rows if row.get('tds_applicable')]
    if flagged:
        return _q(sum((Decimal(r['amount']) for r in flagged), ZERO))
    if not earning_rows:
        return ZERO
    return _q(sum((Decimal(r['amount']) for r in earning_rows), ZERO))


def sum_previous_employer(employee, financial_year: str) -> tuple[Decimal, Decimal]:
    qs = PreviousEmployerIncome.objects.filter(
        employee=employee,
        financial_year=financial_year,
    )
    agg = qs.aggregate(
        income=Sum('taxable_income'),
        tds=Sum('tds_deducted'),
    )
    return _q(agg['income'] or 0), _q(agg['tds'] or 0)


def sum_ytd_payroll_taxable_and_tds(
    employee,
    *,
    financial_year: str,
    before_period_start: date,
    exclude_run_id: int | None = None,
) -> tuple[Decimal, Decimal]:
    """Sum YTD taxable salary and TDS from prior locked/calculated results in FY.

    Uses ``PayrollTDSResult`` snapshots when present; falls back to gross and
    STAT_TDS component amounts.
    """
    from apps.compliance.models import PayrollTDSResult
    from apps.payroll.models import PayrollResult, PayrollResultComponent, PayrollRunStatus

    fy_start, _ = fy_date_bounds(financial_year)
    allowed = {
        PayrollRunStatus.CALCULATED,
        PayrollRunStatus.REVIEWED,
        PayrollRunStatus.APPROVED,
        PayrollRunStatus.LOCKED,
    }
    results = (
        PayrollResult.objects
        .filter(
            employee=employee,
            run__status__in=allowed,
            run__period__end_date__gte=fy_start,
            run__period__end_date__lt=before_period_start,
        )
        .select_related('run', 'run__period')
    )
    if exclude_run_id:
        results = results.exclude(run_id=exclude_run_id)

    ytd_taxable = ZERO
    ytd_tds = ZERO
    for result in results:
        try:
            tds_row = result.tds_result
        except PayrollTDSResult.DoesNotExist:
            tds_row = None
        if tds_row is not None:
            snap = tds_row.calculation_snapshot or {}
            month_taxable = snap.get('current_month_taxable')
            if month_taxable is not None:
                ytd_taxable += _q(month_taxable)
            else:
                ytd_taxable += _q(result.gross)
            ytd_tds += _q(tds_row.monthly_tds)
        else:
            ytd_taxable += _q(result.gross)
            comp = (
                PayrollResultComponent.objects
                .filter(result=result, component_code='STAT_TDS')
                .first()
            )
            if comp:
                ytd_tds += _q(comp.amount)
    return _q(ytd_taxable), _q(ytd_tds)


def resolve_declaration_deductions(
    employee,
    *,
    financial_year: str,
    regime: str,
) -> tuple[Decimal, TaxDeclaration | None]:
    """OLD-regime chapter VIA / HRA / housing etc. from approved/submitted declaration."""
    decl = (
        TaxDeclaration.objects
        .filter(employee=employee, financial_year=financial_year)
        .order_by('-updated_at')
        .first()
    )
    if decl is None:
        return ZERO, None
    if decl.status not in {TaxDeclarationStatus.APPROVED, TaxDeclarationStatus.SUBMITTED}:
        return ZERO, decl
    if regime != TaxRegime.OLD:
        return ZERO, decl
    return _q(decl.total_old_regime_deductions()), decl


def project_annual_income(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule,
    regime: str,
    exclude_run_id: int | None = None,
) -> IncomeProjection:
    """Build annual taxable income projection for TDS."""
    as_of = period.end_date
    fy = financial_year_for_date(as_of)
    current = determine_taxable_salary_from_components(earning_rows)
    months_left = remaining_months_in_fy(as_of)
    # Future months after current: months_left - 1
    future_months = max(0, months_left - 1)
    projected_future = _q(current * future_months)

    ytd_taxable, ytd_tds = sum_ytd_payroll_taxable_and_tds(
        employee,
        financial_year=fy,
        before_period_start=period.start_date,
        exclude_run_id=exclude_run_id,
    )
    prev_income, prev_tds = sum_previous_employer(employee, fy)

    projected_annual = _q(ytd_taxable + current + projected_future + prev_income)
    std = _q(rule.standard_deduction)
    old_ded, decl = resolve_declaration_deductions(
        employee, financial_year=fy, regime=regime,
    )

    taxable = projected_annual - std
    if regime == TaxRegime.OLD:
        taxable -= old_ded
    taxable = max(ZERO, _q(taxable))

    return IncomeProjection(
        financial_year=fy,
        ytd_taxable=ytd_taxable,
        current_month_taxable=current,
        remaining_months_including_current=months_left,
        projected_future_months=projected_future,
        previous_employer_income=prev_income,
        previous_employer_tds=prev_tds,
        ytd_payroll_tds=ytd_tds,
        projected_annual_income=projected_annual,
        standard_deduction=std,
        old_regime_deductions=old_ded,
        taxable_income=taxable,
        detail={
            'declaration_id': decl.pk if decl else None,
            'declaration_status': decl.status if decl else '',
            'projection_basis': (
                'ytd_prior + current + (remaining_after_current * current) + previous_employer'
            ),
            'regime': regime,
            'rule_code': rule.code,
            'standard_deduction_applied': str(std),
        },
    )
