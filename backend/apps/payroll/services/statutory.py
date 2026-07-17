"""Statutory contribution hooks (PF / ESI / PT / TDS) — stubs for Sprint 7 / Sprint 8 prep."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def calculate_employee_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Employee PF contribution stub (12% of basic)."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employer_pf(basic: Decimal, *, rate: Decimal = Decimal('0.12')) -> Decimal:
    """Employer PF contribution stub."""
    return (Decimal(basic) * rate).quantize(Decimal('0.01'))


def calculate_employee_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0075')) -> Decimal:
    """Employee ESI stub (0.75% of gross) — eligibility checks deferred to Sprint 8."""
    return (Decimal(gross) * rate).quantize(Decimal('0.01'))


def calculate_employer_esi(gross: Decimal, *, rate: Decimal = Decimal('0.0325')) -> Decimal:
    """Employer ESI stub (3.25% of gross)."""
    return (Decimal(gross) * rate).quantize(Decimal('0.01'))


def calculate_professional_tax(gross: Decimal, *, state: str = '') -> Decimal:
    """Professional tax stub — state slabs deferred."""
    _ = state
    if Decimal(gross) >= Decimal('15000'):
        return Decimal('200.00')
    return Decimal('0.00')


def calculate_tds(taxable_income: Decimal, *, regime: str = 'new') -> Decimal:
    """TDS stub — full tax engine deferred to later sprint."""
    _ = regime
    income = Decimal(taxable_income)
    if income <= Decimal('50000'):
        return Decimal('0.00')
    return ((income - Decimal('50000')) * Decimal('0.10')).quantize(Decimal('0.01'))


def statutory_summary(
    *,
    basic: Decimal,
    gross: Decimal,
    taxable: Decimal | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Decimal]:
    """Aggregate stub statutory amounts for a payslip preview."""
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
