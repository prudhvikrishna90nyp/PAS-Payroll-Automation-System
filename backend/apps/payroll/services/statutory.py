"""Statutory contribution hooks — EPF via compliance engine; ESI/PT/TDS stubs (Sprint 9.1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.compliance.services.pf_engine import (
    PFCalculationResult,
    build_pf_component_rows,
    calculate_pf,
)


def calculate_employee_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Legacy helper: 12% of basic (prefer ``calculate_pf`` for full EPF)."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employer_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Legacy helper: employer PF stub on basic."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employee_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0075')) -> Decimal:
    """Employee ESI stub (0.75%) — Sprint 9.2."""
    _ = gross, rate
    return Decimal('0.00')


def calculate_employer_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0325')) -> Decimal:
    """Employer ESI stub (3.25%) — Sprint 9.2."""
    _ = gross, rate
    return Decimal('0.00')


def calculate_professional_tax(gross: Decimal, *, state: str = '') -> Decimal:
    """Professional tax stub — state slabs in Sprint 9.3."""
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


def statutory_component_rows(
    *,
    employee,
    period,
    earning_rows: list[dict],
    gross: Decimal,
    rule_set=None,
    ncp_days: Decimal | None = None,
) -> tuple[list[dict], PFCalculationResult]:
    """Build PF (+ stub ESI/PT/TDS) component rows and return the PF result."""
    from apps.payroll.models import ComponentType

    pf = compute_run_pf(
        employee=employee,
        period=period,
        earning_rows=earning_rows,
        rule_set=rule_set,
        ncp_days=ncp_days,
    )
    rows = build_pf_component_rows(pf)

    # Sprint 9.2–9.4 placeholders (zero amounts)
    rows.extend([
        {
            'component_code': 'STAT_ESI',
            'component_name': 'ESI (planned Sprint 9.2)',
            'component_type': ComponentType.DEDUCTION,
            'amount': calculate_employee_esi(gross),
            'calculation_detail': {'placeholder': True, 'sprint': '9.2'},
        },
        {
            'component_code': 'STAT_PT',
            'component_name': 'Professional Tax (planned Sprint 9.3)',
            'component_type': ComponentType.DEDUCTION,
            'amount': calculate_professional_tax(gross),
            'calculation_detail': {'placeholder': True, 'sprint': '9.3'},
        },
        {
            'component_code': 'STAT_TDS',
            'component_name': 'TDS (planned Sprint 9.4)',
            'component_type': ComponentType.DEDUCTION,
            'amount': calculate_tds(gross),
            'calculation_detail': {'placeholder': True, 'sprint': '9.4'},
        },
    ])
    return rows, pf


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
