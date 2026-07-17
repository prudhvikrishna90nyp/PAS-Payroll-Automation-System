"""Deductions helpers for payroll calculation (Sprint 8.2).

Structure deductions are prorated with the same factor as earnings.
Statutory PF/ESI/PT/TDS are injected as zero placeholders by the calculator
until Sprint 9.
"""

from __future__ import annotations

from decimal import Decimal

from apps.payroll.models import ComponentType
from apps.payroll.services.earnings import prorate_amount

ZERO = Decimal('0.00')


def build_deduction_rows(lines: list[dict], factor: Decimal) -> list[dict]:
    """Build prorated structure deduction rows (excludes statutory placeholders)."""
    rows: list[dict] = []
    for line in lines:
        if line.get('component_type') != ComponentType.DEDUCTION:
            continue
        full_amount = Decimal(line['amount'])
        amount = prorate_amount(full_amount, factor)
        rows.append({
            'component_code': line['component_code'],
            'component_name': line['component_name'],
            'component_type': ComponentType.DEDUCTION,
            'amount': amount,
            'calculation_detail': {
                'calculation_type': line.get('calculation_type'),
                'full_month_amount': str(full_amount),
                'proration_factor': str(factor),
                'prorated': True,
            },
        })
    return rows


def statutory_placeholder_total() -> Decimal:
    """Sprint 9 deferred — always zero for Sprint 8.2."""
    return ZERO
