"""Income-tax / TDS rule loading and FY seed data (Sprint 9.4).

Slabs and rates documented here are written to the DB by ``seed_tds_rule_sets``.
The calculation engine must NEVER hardcode these amounts — it loads
``FinancialYearTaxRule`` + ``TaxSlab`` rows for the resolved rule.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.compliance.models import FinancialYearTaxRule, TaxRegime, TaxSlab


# ---------------------------------------------------------------------------
# Documented seed sources (approximate official structure for auditors)
# ---------------------------------------------------------------------------
# FY 2024-25 NEW: Budget 2024 revised new-regime slabs; std deduction ₹75,000;
#   rebate u/s 87A effectively nil tax up to taxable income ₹7,00,000.
# FY 2024-25 OLD: classic slabs; std deduction ₹50,000; rebate income ≤ ₹5L.
# FY 2025-26 NEW: Budget 2025 revised slabs; rebate income ≤ ₹12,00,000;
#   std deduction ₹75,000.
# FY 2025-26 OLD: same classic slabs as prior seed; std deduction ₹50,000.
# Cess: 4% Health & Education Cess on (tax + surcharge) — both FYs.
# Surcharge bands (simplified PAS seed — stored in JSON, not engine constants).
# ---------------------------------------------------------------------------

DEFAULT_CESS = Decimal('0.0400')

# Shared surcharge bands (taxable income thresholds in rupees).
SURCHARGE_BANDS = [
    {'income_from': '5000000', 'income_to': '10000000', 'rate': '0.10'},
    {'income_from': '10000000', 'income_to': '20000000', 'rate': '0.15'},
    {'income_from': '20000000', 'income_to': '50000000', 'rate': '0.25'},
    {'income_from': '50000000', 'income_to': None, 'rate': '0.37'},
]

# NEW regime surcharge top band often capped at 25% — seed a NEW-specific set.
SURCHARGE_BANDS_NEW = [
    {'income_from': '5000000', 'income_to': '10000000', 'rate': '0.10'},
    {'income_from': '10000000', 'income_to': '20000000', 'rate': '0.15'},
    {'income_from': '20000000', 'income_to': None, 'rate': '0.25'},
]

# (income_from, income_to|None, rate, sequence)
SLABS_OLD = (
    (Decimal('0.00'), Decimal('250000.00'), Decimal('0.0000'), 10),
    (Decimal('250000.01'), Decimal('500000.00'), Decimal('0.0500'), 20),
    (Decimal('500000.01'), Decimal('1000000.00'), Decimal('0.2000'), 30),
    (Decimal('1000000.01'), None, Decimal('0.3000'), 40),
)

SLABS_NEW_2024_25 = (
    (Decimal('0.00'), Decimal('300000.00'), Decimal('0.0000'), 10),
    (Decimal('300000.01'), Decimal('700000.00'), Decimal('0.0500'), 20),
    (Decimal('700000.01'), Decimal('1000000.00'), Decimal('0.1000'), 30),
    (Decimal('1000000.01'), Decimal('1200000.00'), Decimal('0.1500'), 40),
    (Decimal('1200000.01'), Decimal('1500000.00'), Decimal('0.2000'), 50),
    (Decimal('1500000.01'), None, Decimal('0.3000'), 60),
)

SLABS_NEW_2025_26 = (
    (Decimal('0.00'), Decimal('400000.00'), Decimal('0.0000'), 10),
    (Decimal('400000.01'), Decimal('800000.00'), Decimal('0.0500'), 20),
    (Decimal('800000.01'), Decimal('1200000.00'), Decimal('0.1000'), 30),
    (Decimal('1200000.01'), Decimal('1600000.00'), Decimal('0.1500'), 40),
    (Decimal('1600000.01'), Decimal('2000000.00'), Decimal('0.2000'), 50),
    (Decimal('2000000.01'), Decimal('2400000.00'), Decimal('0.2500'), 60),
    (Decimal('2400000.01'), None, Decimal('0.3000'), 70),
)

# Regime-change deadline: 31 July of the FY start calendar year.
REGIME_CHANGE_DEADLINE_MONTH = 7
REGIME_CHANGE_DEADLINE_DAY = 31


def financial_year_for_date(as_of: date) -> str:
    """Return Indian FY label (Apr–Mar), e.g. 2024-04-01 → '2024-25'."""
    if as_of.month >= 4:
        start = as_of.year
    else:
        start = as_of.year - 1
    return f'{start}-{str(start + 1)[-2:]}'


def fy_date_bounds(financial_year: str) -> tuple[date, date]:
    """Inclusive start/end dates for an FY label like '2024-25'."""
    start_year = int(financial_year.split('-')[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def regime_change_deadline(financial_year: str) -> date:
    """Last date an employee may change regime for payroll in this FY."""
    start_year = int(financial_year.split('-')[0])
    return date(start_year, REGIME_CHANGE_DEADLINE_MONTH, REGIME_CHANGE_DEADLINE_DAY)


def months_in_fy_up_to(as_of: date) -> int:
    """1-based month index within FY (Apr=1 … Mar=12) for ``as_of``."""
    fy_start, _ = fy_date_bounds(financial_year_for_date(as_of))
    return (as_of.year - fy_start.year) * 12 + (as_of.month - fy_start.month) + 1


def remaining_months_in_fy(as_of: date) -> int:
    """Months left in FY including the current month."""
    idx = months_in_fy_up_to(as_of)
    return max(1, 13 - idx)


def get_tax_rule_for_fy_regime_and_date(
    financial_year: str,
    tax_regime: str,
    as_of: date,
    *,
    require_active: bool = True,
) -> FinancialYearTaxRule:
    """Resolve the FY tax rule effective on ``as_of``."""
    fy = (financial_year or '').strip()
    regime = (tax_regime or '').strip().upper()
    if not fy:
        raise ValidationError('financial_year is required to resolve a tax rule.')
    if regime not in {TaxRegime.OLD, TaxRegime.NEW}:
        raise ValidationError(f'Invalid tax_regime: {tax_regime!r}.')
    qs = FinancialYearTaxRule.objects.filter(
        financial_year=fy,
        tax_regime=regime,
        effective_from__lte=as_of,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
    )
    if require_active:
        qs = qs.filter(is_active=True)
    rule = qs.order_by('-effective_from', '-id').first()
    if rule is None:
        raise ValidationError(
            f'No active tax rule for FY {fy} / {regime} on {as_of.isoformat()}.'
        )
    return rule


def _upsert_rule(
    *,
    code: str,
    financial_year: str,
    tax_regime: str,
    effective_from: date,
    standard_deduction: Decimal,
    rebate_limit: Decimal,
    surcharge_rules: list,
    slabs: tuple,
    notes: str,
    force_slabs: bool,
) -> FinancialYearTaxRule:
    defaults = {
        'financial_year': financial_year,
        'tax_regime': tax_regime,
        'name': f'India TDS {financial_year} {tax_regime}',
        'effective_from': effective_from,
        'effective_to': None,
        'standard_deduction': standard_deduction,
        'rebate_limit': rebate_limit,
        'cess_rate': DEFAULT_CESS,
        'surcharge_rules': surcharge_rules,
        'is_active': True,
        'notes': notes,
    }
    obj = FinancialYearTaxRule.objects.filter(code=code).first()
    if obj is None:
        obj = FinancialYearTaxRule(code=code, **defaults)
        obj.save()
        force_slabs = True
    elif force_slabs:
        for key, value in defaults.items():
            setattr(obj, key, value)
        obj.save()

    if force_slabs or not obj.slabs.exists():
        obj.slabs.all().delete()
        TaxSlab.objects.bulk_create([
            TaxSlab(
                rule=obj,
                income_from=income_from,
                income_to=income_to,
                rate=rate,
                sequence=sequence,
            )
            for income_from, income_to, rate, sequence in slabs
        ])
    return obj


def seed_tds_rule_sets(*, force_slabs: bool = False) -> list[FinancialYearTaxRule]:
    """Create or update seeded FY tax rules for OLD/NEW (idempotent)."""
    rules = [
        _upsert_rule(
            code='IN-TDS-OLD-2024-25',
            financial_year='2024-25',
            tax_regime=TaxRegime.OLD,
            effective_from=date(2024, 4, 1),
            standard_deduction=Decimal('50000.00'),
            rebate_limit=Decimal('500000.00'),
            surcharge_rules=SURCHARGE_BANDS,
            slabs=SLABS_OLD,
            notes=(
                'Seeded Sprint 9.4 OLD regime FY 2024-25. '
                'Source: Income-tax Act classic slabs; std deduction ₹50,000; '
                'rebate u/s 87A for taxable income ≤ ₹5,00,000; cess 4%. '
                'Engine loads slabs from DB — never hardcodes these rates.'
            ),
            force_slabs=force_slabs,
        ),
        _upsert_rule(
            code='IN-TDS-NEW-2024-25',
            financial_year='2024-25',
            tax_regime=TaxRegime.NEW,
            effective_from=date(2024, 4, 1),
            standard_deduction=Decimal('75000.00'),
            rebate_limit=Decimal('700000.00'),
            surcharge_rules=SURCHARGE_BANDS_NEW,
            slabs=SLABS_NEW_2024_25,
            notes=(
                'Seeded Sprint 9.4 NEW regime FY 2024-25. '
                'Source: Budget 2024 revised new-regime slabs; std deduction ₹75,000; '
                'rebate u/s 87A for taxable income ≤ ₹7,00,000; cess 4%. '
                'Engine loads slabs from DB — never hardcodes these rates.'
            ),
            force_slabs=force_slabs,
        ),
        _upsert_rule(
            code='IN-TDS-OLD-2025-26',
            financial_year='2025-26',
            tax_regime=TaxRegime.OLD,
            effective_from=date(2025, 4, 1),
            standard_deduction=Decimal('50000.00'),
            rebate_limit=Decimal('500000.00'),
            surcharge_rules=SURCHARGE_BANDS,
            slabs=SLABS_OLD,
            notes=(
                'Seeded Sprint 9.4 OLD regime FY 2025-26. '
                'Source: Income-tax Act classic slabs (unchanged in seed); '
                'std deduction ₹50,000; rebate ≤ ₹5,00,000; cess 4%.'
            ),
            force_slabs=force_slabs,
        ),
        _upsert_rule(
            code='IN-TDS-NEW-2025-26',
            financial_year='2025-26',
            tax_regime=TaxRegime.NEW,
            effective_from=date(2025, 4, 1),
            standard_deduction=Decimal('75000.00'),
            rebate_limit=Decimal('1200000.00'),
            surcharge_rules=SURCHARGE_BANDS_NEW,
            slabs=SLABS_NEW_2025_26,
            notes=(
                'Seeded Sprint 9.4 NEW regime FY 2025-26. '
                'Source: Budget 2025 revised new-regime slabs; std deduction ₹75,000; '
                'rebate u/s 87A for taxable income ≤ ₹12,00,000; cess 4%.'
            ),
            force_slabs=force_slabs,
        ),
    ]
    return rules
