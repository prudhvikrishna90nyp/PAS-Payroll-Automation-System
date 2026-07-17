"""ESI rule loading and default seed (Sprint 9.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.compliance.models import ESIRuleSet, RoundingMethod


# Documented default rates — see models.py header comments.
# EE 0.75%, ER 3.25%, wage limit ₹21,000, daily wage exemption ₹176.
DEFAULT_RULE_CODE = 'IN-ESI-2024'
DEFAULT_EFFECTIVE_FROM = date(2024, 4, 1)
DEFAULT_RATES = {
    'eligibility_wage_limit': Decimal('21000.00'),
    'employee_rate': Decimal('0.0075'),
    'employer_rate': Decimal('0.0325'),
    'daily_wage_exemption_limit': Decimal('176.00'),
    'rounding_method': RoundingMethod.HALF_UP,
}


def get_esi_rule_for_date(as_of: date, *, require_active: bool = True) -> ESIRuleSet:
    """Resolve the ESI rule set effective on ``as_of`` (typically period end date)."""
    qs = ESIRuleSet.objects.filter(effective_from__lte=as_of).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
    )
    if require_active:
        qs = qs.filter(is_active=True)
    rule = qs.order_by('-effective_from', '-id').first()
    if rule is None:
        raise ValidationError(
            f'No active ESI rule set found for date {as_of.isoformat()}.'
        )
    return rule


def seed_default_esi_rule_set(*, force_rates: bool = False) -> ESIRuleSet:
    """Create or update the default India ESI rule set (idempotent)."""
    defaults = {
        'name': 'India ESI (post-2019 typical rates)',
        'effective_from': DEFAULT_EFFECTIVE_FROM,
        'effective_to': None,
        'is_active': True,
        'notes': (
            'Seeded Sprint 9.2 defaults: eligibility wage limit 21000; '
            'EE 0.75%; ER 3.25%; daily wage exemption 176; HALF_UP rounding. '
            'Verified against common ESIC practice (EE/ER cut effective July 2019; '
            'ceiling ₹21,000 from Jan 2017).'
        ),
        **DEFAULT_RATES,
    }
    obj, created = ESIRuleSet.objects.get_or_create(
        code=DEFAULT_RULE_CODE,
        defaults=defaults,
    )
    if not created and force_rates:
        for key, value in defaults.items():
            setattr(obj, key, value)
        obj.save()
    return obj
