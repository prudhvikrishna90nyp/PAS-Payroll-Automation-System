"""PF rule loading and default seed (Sprint 9.1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.compliance.models import PFRuleSet


# Documented default rates — see models.py header comments.
DEFAULT_RULE_CODE = 'IN-EPF-2024'
DEFAULT_EFFECTIVE_FROM = date(2024, 4, 1)
DEFAULT_RATES = {
    'pf_wage_ceiling': Decimal('15000.00'),
    'employee_pf_rate': Decimal('0.1200'),
    'employer_pf_rate': Decimal('0.1200'),
    'eps_rate': Decimal('0.0833'),
    'edli_rate': Decimal('0.0050'),
    'admin_charge': Decimal('0.0050'),
    'inspection_charge': Decimal('0.0000'),
}


def get_pf_rule_for_date(as_of: date, *, require_active: bool = True) -> PFRuleSet:
    """Resolve the PF rule set effective on ``as_of`` (typically period end date)."""
    qs = PFRuleSet.objects.filter(effective_from__lte=as_of).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
    )
    if require_active:
        qs = qs.filter(is_active=True)
    rule = qs.order_by('-effective_from', '-id').first()
    if rule is None:
        raise ValidationError(
            f'No active PF rule set found for date {as_of.isoformat()}.'
        )
    return rule


def seed_default_pf_rule_set(*, force_rates: bool = False) -> PFRuleSet:
    """Create or update the default India EPF rule set (idempotent)."""
    defaults = {
        'name': 'India EPF (FY 2024-25 typical rates)',
        'effective_from': DEFAULT_EFFECTIVE_FROM,
        'effective_to': None,
        'is_active': True,
        'notes': (
            'Seeded Sprint 9.1 defaults: ceiling 15000; EE/ER 12%; EPS 8.33%; '
            'EDLI 0.50%; admin 0.50%; inspection 0.00%.'
        ),
        **DEFAULT_RATES,
    }
    obj, created = PFRuleSet.objects.get_or_create(
        code=DEFAULT_RULE_CODE,
        defaults=defaults,
    )
    if not created and force_rates:
        for key, value in defaults.items():
            setattr(obj, key, value)
        obj.save()
    return obj
