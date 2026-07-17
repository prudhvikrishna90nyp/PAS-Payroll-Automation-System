"""Earnings helpers for payroll calculation (Sprint 8.2)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from apps.payroll.models import ComponentType

TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def prorate_amount(amount: Decimal, factor: Decimal) -> Decimal:
    """Apply proration factor and quantize to paisa."""
    return (Decimal(amount) * Decimal(factor)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def build_earning_rows(lines: list[dict], factor: Decimal) -> list[dict]:
    """Build prorated earning component rows from structure calculation lines."""
    rows: list[dict] = []
    for line in lines:
        if line.get('component_type') != ComponentType.EARNING:
            continue
        full_amount = Decimal(line['amount'])
        amount = prorate_amount(full_amount, factor)
        rows.append({
            'component_code': line['component_code'],
            'component_name': line['component_name'],
            'component_type': ComponentType.EARNING,
            'amount': amount,
            'include_in_gross': line.get('include_in_gross', True),
            'calculation_detail': {
                'calculation_type': line.get('calculation_type'),
                'full_month_amount': str(full_amount),
                'proration_factor': str(factor),
                'prorated': True,
            },
        })
    return rows
