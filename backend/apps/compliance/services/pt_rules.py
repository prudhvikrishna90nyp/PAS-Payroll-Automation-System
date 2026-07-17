"""Professional Tax rule loading and Andhra Pradesh seed (Sprint 9.3).

AP slabs are documented here and written to the DB by ``seed_ap_pt_rule_set``.
The calculation engine must NEVER hardcode these amounts — it loads slabs
from ``ProfessionalTaxSlab`` for the resolved rule set.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.compliance.models import (
    PTFrequency,
    ProfessionalTaxRuleSet,
    ProfessionalTaxSlab,
)


# Documented Andhra Pradesh salaried PT structure (see models.py header).
# Source: AP Tax on Professions, Trades, Callings and Employments Act —
# commonly published commercial-tax / payroll rate card.
AP_STATE_CODE = 'AP'
AP_RULE_NAME = 'Andhra Pradesh Professional Tax (salaried)'
AP_EFFECTIVE_FROM = date(2024, 4, 1)
AP_SPECIAL_MONTH = 2  # February — top slab ₹300 instead of ₹200

# (salary_from, salary_to|None, tax_amount, special_month_tax_amount, sequence)
AP_SLABS = (
    (Decimal('0.00'), Decimal('15000.00'), Decimal('0.00'), Decimal('0.00'), 10),
    (Decimal('15001.00'), Decimal('20000.00'), Decimal('150.00'), Decimal('150.00'), 20),
    (Decimal('20001.00'), None, Decimal('200.00'), Decimal('300.00'), 30),
)


def get_pt_rule_for_state_and_date(
    state_code: str,
    as_of: date,
    *,
    require_active: bool = True,
) -> ProfessionalTaxRuleSet:
    """Resolve the PT rule set for ``state_code`` effective on ``as_of``."""
    code = (state_code or '').strip().upper()
    if not code:
        raise ValidationError('PT state_code is required to resolve a rule set.')
    qs = ProfessionalTaxRuleSet.objects.filter(
        state_code=code,
        effective_from__lte=as_of,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
    )
    if require_active:
        qs = qs.filter(is_active=True)
    rule = qs.order_by('-effective_from', '-id').first()
    if rule is None:
        raise ValidationError(
            f'No active PT rule set found for state {code} on {as_of.isoformat()}.'
        )
    return rule


def seed_ap_pt_rule_set(*, force_slabs: bool = False) -> ProfessionalTaxRuleSet:
    """Create or update the default Andhra Pradesh PT rule set + slabs (idempotent).

    Rates (documented; written to DB only — not used by the engine directly):
      Up to ₹15,000 → ₹0 (incl. February)
      ₹15,001–₹20,000 → ₹150 (incl. February)
      Above ₹20,000 → ₹200; February special month → ₹300
    Special month: February (2).
    """
    defaults = {
        'name': AP_RULE_NAME,
        'effective_from': AP_EFFECTIVE_FROM,
        'effective_to': None,
        'frequency': PTFrequency.MONTHLY,
        'special_month': AP_SPECIAL_MONTH,
        'is_active': True,
        'notes': (
            'Seeded Sprint 9.3 Andhra Pradesh salaried PT slabs. '
            'Source: AP Tax on Professions, Trades, Callings and Employments Act '
            '(commonly published commercial-tax / payroll rate card). '
            'Special month = February (highest slab ₹300). '
            'Engine loads slabs from DB — never hardcodes these amounts.'
        ),
    }
    # Prefer lookup by state + open-ended active window to avoid duplicates.
    obj = (
        ProfessionalTaxRuleSet.objects
        .filter(state_code=AP_STATE_CODE, is_active=True)
        .order_by('-effective_from', '-id')
        .first()
    )
    if obj is None:
        obj = ProfessionalTaxRuleSet(state_code=AP_STATE_CODE, **defaults)
        obj.save()
        force_slabs = True
    elif force_slabs:
        for key, value in defaults.items():
            setattr(obj, key, value)
        obj.save()

    if force_slabs or not obj.slabs.exists():
        obj.slabs.all().delete()
        ProfessionalTaxSlab.objects.bulk_create([
            ProfessionalTaxSlab(
                rule_set=obj,
                salary_from=salary_from,
                salary_to=salary_to,
                tax_amount=tax_amount,
                special_month_tax_amount=special_tax,
                sequence=sequence,
            )
            for salary_from, salary_to, tax_amount, special_tax, sequence in AP_SLABS
        ])
    return obj
