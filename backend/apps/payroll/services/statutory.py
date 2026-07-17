"""Statutory contribution hooks — EPF + ESI + PT via compliance engines; TDS stub."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.compliance.services.esi_engine import (
    ESICalculationResult,
    build_esi_component_rows,
    calculate_esi,
)
from apps.compliance.services.pf_engine import (
    PFCalculationResult,
    build_pf_component_rows,
    calculate_pf,
)
from apps.compliance.services.pt_engine import (
    PTCalculationResult,
    build_pt_component_rows,
    calculate_pt,
)


def calculate_employee_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Legacy helper: 12% of basic (prefer ``calculate_pf`` for full EPF)."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employer_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Legacy helper: employer PF stub on basic."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employee_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0075')) -> Decimal:
    """Legacy helper — prefer ``calculate_esi`` for full ESI (Sprint 9.2)."""
    return (Decimal(gross) * rate).quantize(Decimal('0.01'))


def calculate_employer_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0325')) -> Decimal:
    """Legacy helper — prefer ``calculate_esi`` for full ESI (Sprint 9.2)."""
    return (Decimal(gross) * rate).quantize(Decimal('0.01'))


def calculate_professional_tax(gross: Decimal, *, state: str = '') -> Decimal:
    """Legacy helper — prefer ``calculate_pt`` for full PT (Sprint 9.3)."""
    _ = gross, state
    return Decimal('0.00')


def calculate_tds(taxable_income: Decimal, *, regime: str = 'new') -> Decimal:
    """TDS stub — full tax engine in Sprint 9.4."""
    _ = taxable_income, regime
    return Decimal('0.00')


def compute_run_pf(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set=None,
    ncp_days: Decimal | None = None,
) -> PFCalculationResult:
    """Full EPF calculation for payroll engine integration."""
    return calculate_pf(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=rule_set,
        ncp_days=ncp_days,
    )


def compute_run_esi(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set=None,
    payable_days: Decimal | None = None,
    calendar_days: Decimal | None = None,
) -> ESICalculationResult:
    """Full ESI calculation for payroll engine integration."""
    return calculate_esi(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=rule_set,
        payable_days=payable_days,
        calendar_days=calendar_days,
    )


def compute_run_pt(
    *,
    employee,
    period,
    earning_rows: list[dict],
    rule_set=None,
) -> PTCalculationResult:
    """Full Professional Tax calculation for payroll engine integration."""
    return calculate_pt(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=rule_set,
    )


def statutory_component_rows(
    *,
    employee,
    period,
    earning_rows: list[dict],
    gross: Decimal,
    rule_set=None,
    esi_rule_set=None,
    pt_rule_set=None,
    ncp_days: Decimal | None = None,
    payable_days: Decimal | None = None,
    calendar_days: Decimal | None = None,
) -> tuple[list[dict], PFCalculationResult, ESICalculationResult, PTCalculationResult]:
    """Build PF + ESI + PT (+ stub TDS) component rows and return calc results."""
    from apps.payroll.models import ComponentType

    pf = compute_run_pf(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=rule_set,
        ncp_days=ncp_days,
    )
    esi = compute_run_esi(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=esi_rule_set,
        payable_days=payable_days,
        calendar_days=calendar_days,
    )
    pt = compute_run_pt(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=pt_rule_set,
    )
    rows = build_pf_component_rows(pf)
    rows.extend(build_esi_component_rows(esi))
    rows.extend(build_pt_component_rows(pt))

    # Sprint 9.4 placeholder (zero amount)
    rows.append({
        'component_code': 'STAT_TDS',
        'component_name': 'TDS (planned Sprint 9.4)',
        'component_type': ComponentType.DEDUCTION,
        'amount': calculate_tds(gross),
        'calculation_detail': {'placeholder': True, 'sprint': '9.4'},
    })
    return rows, pf, esi, pt


def statutory_summary(
    *,
    basic: Decimal,
    gross: Decimal,
    taxable: Decimal | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Decimal]:
    """Aggregate statutory amounts for legacy payslip preview."""
    _ = context
    taxable = Decimal(taxable if taxable is not None else gross)
    return {
        'ee_pf': calculate_employee_pf(basic),
        'er_pf': calculate_employer_pf(basic),
        'ee_esi': calculate_employee_esi(gross),
        'er_esi': calculate_employer_esi(gross),
        'pt': calculate_professional_tax(gross),
        'tds': calculate_tds(taxable),
    }
