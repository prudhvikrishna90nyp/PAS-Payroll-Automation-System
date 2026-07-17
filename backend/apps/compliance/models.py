"""EPF / ESI / Professional Tax / TDS statutory compliance models (Sprint 9.1–9.4)."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.validators import validate_esi_ip, validate_pan, validate_uan
from apps.employee.models import Employee


# ---------------------------------------------------------------------------
# Default India EPF rates (document for auditors / future rule changes)
# ---------------------------------------------------------------------------
# Commonly applied rates from FY 2018-19 onward; still typical for FY 2024-25
# (effective_from seed: 2024-04-01):
#   - PF wage ceiling: ₹15,000 / month
#   - Employee EPF: 12% of PF wages
#   - Employer total: 12% of PF wages, split as:
#       EPS  8.33% of PF wages (capped at ceiling unless higher pension)
#       EPF  remainder (≈ 3.67% when wages are at/above ceiling)
#   - EDLI: 0.50% of PF wages (capped at ceiling)
#   - Admin charges: 0.50% of PF wages (EPFO; was historically 0.65%)
#   - Inspection charges: 0.00% (abolished; field retained for history)
# ---------------------------------------------------------------------------


class PFRuleSet(models.Model):
    """Versioned EPF rate set. Active rows must not overlap by date range."""

    name = models.CharField(max_length=100, default='India EPF')
    code = models.CharField(
        max_length=30,
        unique=True,
        help_text='Stable identifier snapshotted on payroll results (e.g. IN-EPF-2024).',
    )
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Inclusive end date. Null means open-ended.',
    )
    pf_wage_ceiling = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('15000.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    employee_pf_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.1200'),
        help_text='Employee EPF rate as a fraction (0.12 = 12%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    employer_pf_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.1200'),
        help_text='Total employer contribution rate (EPS + employer EPF).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    eps_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0833'),
        help_text='EPS share of employer contribution (typically 8.33%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    edli_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0050'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    admin_charge = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0050'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    inspection_charge = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from', 'code']
        verbose_name = 'PF Rule Set'
        verbose_name_plural = 'PF Rule Sets'
        permissions = [
            ('export_pfregister', 'Can export PF registers'),
            ('export_ecr', 'Can export EPFO ECR'),
        ]

    def __str__(self):
        end = self.effective_to or 'open'
        return f'{self.code} ({self.effective_from} – {end})'

    def clean(self):
        errors = {}
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'effective_to must be on or after effective_from.'
        if self.eps_rate is not None and self.employer_pf_rate is not None:
            if self.eps_rate > self.employer_pf_rate:
                errors['eps_rate'] = 'EPS rate cannot exceed employer PF rate.'
        if self.effective_from and self.is_active:
            overlap = self._overlapping_active_queryset()
            if overlap.exists():
                other = overlap.first()
                errors['__all__'] = (
                    f'Active date range overlaps rule set {other.code} '
                    f'({other.effective_from} – {other.effective_to or "open"}).'
                )
        if errors:
            raise ValidationError(errors)

    def _overlapping_active_queryset(self):
        """Active PFRuleSets whose date ranges intersect this instance."""
        start = self.effective_from
        end = self.effective_to
        qs = PFRuleSet.objects.filter(is_active=True).exclude(pk=self.pk)
        # Overlap: other.start <= self.end (or self open) AND other.end >= self.start (or other open)
        if end is None:
            qs = qs.filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start))
        else:
            qs = qs.filter(effective_from__lte=end).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=start)
            )
        return qs

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class EmployeePFProfile(models.Model):
    """Per-employee EPF enrolment and contribution options."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='pf_profile',
    )
    uan = models.CharField(max_length=12, blank=True, validators=[validate_uan])
    pf_number = models.CharField(max_length=50, blank=True)
    joining_pf_date = models.DateField(null=True, blank=True)
    exit_pf_date = models.DateField(null=True, blank=True)
    higher_pension = models.BooleanField(
        default=False,
        help_text='If set, EPS is computed on actual PF wages without the statutory ceiling.',
    )
    voluntary_pf = models.BooleanField(default=False)
    vpf_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Voluntary PF as a fraction of PF wages (e.g. 0.05 = 5%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    is_pf_applicable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__employee_code']
        verbose_name = 'Employee PF Profile'
        verbose_name_plural = 'Employee PF Profiles'
        constraints = [
            models.UniqueConstraint(
                fields=['pf_number'],
                condition=~Q(pf_number=''),
                name='uniq_employee_pf_number_nonblank',
            ),
        ]

    def __str__(self):
        return f'PF profile — {self.employee.employee_code}'

    def clean(self):
        errors = {}
        if self.exit_pf_date and self.joining_pf_date and self.exit_pf_date < self.joining_pf_date:
            errors['exit_pf_date'] = 'Exit PF date must be on or after joining PF date.'
        if self.voluntary_pf and (self.vpf_percentage or 0) <= 0:
            errors['vpf_percentage'] = 'VPF percentage is required when voluntary PF is enabled.'
        if self.uan:
            try:
                validate_uan(self.uan)
            except ValidationError as exc:
                errors['uan'] = exc.messages
        if self.pf_number:
            dup = (
                EmployeePFProfile.objects
                .filter(pf_number=self.pf_number)
                .exclude(pk=self.pk)
            )
            if dup.exists():
                errors['pf_number'] = 'This PF number is already assigned to another employee.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.uan:
            self.uan = ''.join(self.uan.split())
        if self.pf_number:
            self.pf_number = self.pf_number.strip()
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class PayrollPFResult(models.Model):
    """Immutable EPF calculation snapshot linked to a payroll result."""

    payroll_result = models.OneToOneField(
        'payroll.PayrollResult',
        on_delete=models.CASCADE,
        related_name='pf_result',
    )
    rule_set = models.ForeignKey(
        PFRuleSet,
        on_delete=models.PROTECT,
        related_name='payroll_pf_results',
        null=True,
        blank=True,
    )
    rule_version = models.CharField(
        max_length=30,
        blank=True,
        help_text='Denormalised PFRuleSet.code at calculation time.',
    )
    pf_wages = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    actual_pf_wages = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Sum of PF-applicable earnings before ceiling.',
    )
    employee_pf = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    voluntary_pf = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    employer_pf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total employer contribution (EPS + employer EPF).',
    )
    eps = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    epf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Employer EPF account share (employer_pf - eps).',
    )
    edli = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    admin_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    inspection_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    ncp_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Non-contributory days (typically LOP) for ECR.',
    )
    calculation_detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payroll_result_id']
        verbose_name = 'Payroll PF Result'
        verbose_name_plural = 'Payroll PF Results'

    def __str__(self):
        return f'PF result for payroll result #{self.payroll_result_id}'


# ---------------------------------------------------------------------------
# Default India ESI rates (document for auditors / future rule changes)
# ---------------------------------------------------------------------------
# Verified against ESIC / ESI Act practice commonly applied from July 2019
# onward (employee rate cut 1.75%→0.75%, employer 4.75%→3.25%) and wage
# ceiling ₹21,000 (raised from ₹15,000 effective 01-Jan-2017). Seed
# effective_from: 2024-04-01 (aligned with EPF seed window; rates unchanged):
#   - Eligibility wage limit: ₹21,000 / month (gross ESI wages)
#   - Employee ESI: 0.75% of ESI wages
#   - Employer ESI: 3.25% of ESI wages
#   - Daily wage exemption: avg daily wage ≤ ₹176 → EE share exempt (ER still due)
#   - Contribution periods: 1 Apr–30 Sep and 1 Oct–31 Mar (continuity rule)
# Rates are NEVER hardcoded in the calculation engine — always load ESIRuleSet.
# ---------------------------------------------------------------------------


class RoundingMethod(models.TextChoices):
    HALF_UP = 'HALF_UP', 'Round half up (2 dp)'
    NEAREST_RUPEE = 'NEAREST_RUPEE', 'Nearest rupee'


class ESIRuleSet(models.Model):
    """Versioned ESI rate set. Active rows must not overlap by date range."""

    name = models.CharField(max_length=100, default='India ESI')
    code = models.CharField(
        max_length=30,
        unique=True,
        help_text='Stable identifier snapshotted on payroll results (e.g. IN-ESI-2024).',
    )
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Inclusive end date. Null means open-ended.',
    )
    eligibility_wage_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('21000.00'),
        help_text='Monthly ESI wage ceiling for first-time eligibility in a contribution period.',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    employee_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0075'),
        help_text='Employee ESI rate as a fraction (0.0075 = 0.75%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    employer_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0325'),
        help_text='Employer ESI rate as a fraction (0.0325 = 3.25%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    daily_wage_exemption_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('176.00'),
        help_text='Avg daily wage at/below this amount → employee share exempt (employer still due).',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    rounding_method = models.CharField(
        max_length=20,
        choices=RoundingMethod.choices,
        default=RoundingMethod.HALF_UP,
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from', 'code']
        verbose_name = 'ESI Rule Set'
        verbose_name_plural = 'ESI Rule Sets'
        permissions = [
            ('export_esiregister', 'Can export ESI registers'),
            ('export_esicontribution', 'Can export ESI contribution data'),
        ]

    def __str__(self):
        end = self.effective_to or 'open'
        return f'{self.code} ({self.effective_from} – {end})'

    def clean(self):
        errors = {}
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'effective_to must be on or after effective_from.'
        if self.effective_from and self.is_active:
            overlap = self._overlapping_active_queryset()
            if overlap.exists():
                other = overlap.first()
                errors['__all__'] = (
                    f'Active date range overlaps rule set {other.code} '
                    f'({other.effective_from} – {other.effective_to or "open"}).'
                )
        if errors:
            raise ValidationError(errors)

    def _overlapping_active_queryset(self):
        start = self.effective_from
        end = self.effective_to
        qs = ESIRuleSet.objects.filter(is_active=True).exclude(pk=self.pk)
        if end is None:
            qs = qs.filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start))
        else:
            qs = qs.filter(effective_from__lte=end).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=start)
            )
        return qs

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class EmployeeESIProfile(models.Model):
    """Per-employee ESI enrolment and contribution-period continuity."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='esi_profile',
    )
    ip_number = models.CharField(
        max_length=17,
        blank=True,
        help_text='ESI Insurance Number (IP). Typically 10 digits; spaces allowed.',
        validators=[validate_esi_ip],
    )
    joining_esi_date = models.DateField(null=True, blank=True)
    exit_esi_date = models.DateField(null=True, blank=True)
    is_esi_applicable = models.BooleanField(default=True)
    is_daily_wage_worker = models.BooleanField(
        default=False,
        help_text='When set, average daily wage uses payable/working days for exemption checks.',
    )
    covered_period_start = models.DateField(
        null=True,
        blank=True,
        help_text=(
            'Start date of the ESI contribution period in which this employee was first covered. '
            'Used for continuity: once covered, remain covered until period end even if wages '
            'exceed the eligibility ceiling (unless exited).'
        ),
    )
    covered_period_end = models.DateField(
        null=True,
        blank=True,
        help_text='End date of the contribution period matching covered_period_start.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__employee_code']
        verbose_name = 'Employee ESI Profile'
        verbose_name_plural = 'Employee ESI Profiles'
        constraints = [
            models.UniqueConstraint(
                fields=['ip_number'],
                condition=~Q(ip_number=''),
                name='uniq_employee_esi_ip_number_nonblank',
            ),
        ]

    def __str__(self):
        return f'ESI profile — {self.employee.employee_code}'

    def clean(self):
        errors = {}
        if self.exit_esi_date and self.joining_esi_date and self.exit_esi_date < self.joining_esi_date:
            errors['exit_esi_date'] = 'Exit ESI date must be on or after joining ESI date.'
        if self.covered_period_start and self.covered_period_end:
            if self.covered_period_end < self.covered_period_start:
                errors['covered_period_end'] = 'covered_period_end must be on or after covered_period_start.'
        if self.ip_number:
            try:
                validate_esi_ip(self.ip_number)
            except ValidationError as exc:
                errors['ip_number'] = exc.messages
        if self.ip_number:
            dup = (
                EmployeeESIProfile.objects
                .filter(ip_number=self.ip_number)
                .exclude(pk=self.pk)
            )
            if dup.exists():
                errors['ip_number'] = 'This ESI IP number is already assigned to another employee.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.ip_number:
            self.ip_number = ''.join(self.ip_number.split())
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class PayrollESIResult(models.Model):
    """Immutable ESI calculation snapshot linked to a payroll result."""

    payroll_result = models.OneToOneField(
        'payroll.PayrollResult',
        on_delete=models.CASCADE,
        related_name='esi_result',
    )
    rule_set = models.ForeignKey(
        ESIRuleSet,
        on_delete=models.PROTECT,
        related_name='payroll_esi_results',
        null=True,
        blank=True,
    )
    rule_version = models.CharField(
        max_length=30,
        blank=True,
        help_text='Denormalised ESIRuleSet.code at calculation time.',
    )
    esi_wages = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    employee_esi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    employer_esi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_eligible = models.BooleanField(default=False)
    above_wage_limit = models.BooleanField(
        default=False,
        help_text='True when ESI wages exceeded eligibility_wage_limit for this period.',
    )
    continuity_applied = models.BooleanField(
        default=False,
        help_text='True when eligibility continued due to contribution-period continuity.',
    )
    daily_wage_exemption = models.BooleanField(
        default=False,
        help_text='True when employee share was exempted due to daily wage limit.',
    )
    missing_ip_number = models.BooleanField(
        default=False,
        help_text='True when employee was ESI-applicable but IP number was missing.',
    )
    eligibility_notes = models.TextField(blank=True)
    calculation_detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payroll_result_id']
        verbose_name = 'Payroll ESI Result'
        verbose_name_plural = 'Payroll ESI Results'

    def __str__(self):
        return f'ESI result for payroll result #{self.payroll_result_id}'


# ---------------------------------------------------------------------------
# Andhra Pradesh Professional Tax (salaried) — documented seed rates
# ---------------------------------------------------------------------------
# Source: Andhra Pradesh Tax on Professions, Trades, Callings and Employments
# Act — commonly published commercial-tax / payroll rate card for employees
# (rates unchanged in recent years; seed effective_from: 2024-04-01):
#
#   | Monthly PT wages              | Monthly tax | February (special) |
#   | Up to ₹15,000                 | Nil (₹0)    | Nil (₹0)           |
#   | ₹15,001 – ₹20,000             | ₹150        | ₹150               |
#   | Above ₹20,000                 | ₹200        | ₹300               |
#
# Special month: FEBRUARY (calendar month 2). Only the top slab differs
# (₹300 instead of ₹200). Frequency for employees: MONTHLY.
#
# CRITICAL: Slabs are NEVER hardcoded in the calculation engine — always
# load ProfessionalTaxSlab rows from the DB for the effective rule set.
# PT jurisdiction is the employee work state (EmployeePTProfile.state_code),
# NOT the company registered address alone.
# ---------------------------------------------------------------------------


class PTFrequency(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half-yearly'
    ANNUAL = 'ANNUAL', 'Annual'


class PTExemptionType(models.TextChoices):
    NONE = '', 'None'
    SENIOR_CITIZEN = 'SENIOR_CITIZEN', 'Senior citizen'
    DISABLED = 'DISABLED', 'Differently abled'
    OTHER = 'OTHER', 'Other / manual exemption'


class ProfessionalTaxRuleSet(models.Model):
    """Versioned state PT rule set. Active rows must not overlap by state + dates."""

    state_code = models.CharField(
        max_length=10,
        help_text='ISO-like state code for PT jurisdiction (e.g. AP, TS, KA).',
        db_index=True,
    )
    name = models.CharField(max_length=100)
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Inclusive end date. Null means open-ended.',
    )
    frequency = models.CharField(
        max_length=20,
        choices=PTFrequency.choices,
        default=PTFrequency.MONTHLY,
    )
    special_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Calendar month (1–12) with alternate slab amounts (e.g. 2 = February for AP).',
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['state_code', '-effective_from']
        verbose_name = 'Professional Tax Rule Set'
        verbose_name_plural = 'Professional Tax Rule Sets'
        permissions = [
            ('export_ptregister', 'Can export PT registers'),
            ('export_ptchallan', 'Can export PT challan / return data'),
        ]

    def __str__(self):
        end = self.effective_to or 'open'
        return f'{self.state_code} — {self.name} ({self.effective_from} – {end})'

    def clean(self):
        errors = {}
        if self.state_code:
            self.state_code = self.state_code.strip().upper()
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'effective_to must be on or after effective_from.'
        if self.special_month is not None and not (1 <= int(self.special_month) <= 12):
            errors['special_month'] = 'special_month must be between 1 and 12.'
        if self.effective_from and self.is_active and self.state_code:
            overlap = self._overlapping_active_queryset()
            if overlap.exists():
                other = overlap.first()
                errors['__all__'] = (
                    f'Active date range overlaps rule set for {other.state_code} '
                    f'({other.name}: {other.effective_from} – {other.effective_to or "open"}).'
                )
        if errors:
            raise ValidationError(errors)

    def _overlapping_active_queryset(self):
        start = self.effective_from
        end = self.effective_to
        qs = ProfessionalTaxRuleSet.objects.filter(
            is_active=True,
            state_code=self.state_code,
        ).exclude(pk=self.pk)
        if end is None:
            qs = qs.filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start))
        else:
            qs = qs.filter(effective_from__lte=end).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=start)
            )
        return qs

    def save(self, *args, **kwargs):
        if self.state_code:
            self.state_code = self.state_code.strip().upper()
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class ProfessionalTaxSlab(models.Model):
    """One salary band within a PT rule set. Amounts come from DB only."""

    rule_set = models.ForeignKey(
        ProfessionalTaxRuleSet,
        on_delete=models.CASCADE,
        related_name='slabs',
    )
    salary_from = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Inclusive lower bound of monthly PT wages.',
    )
    salary_to = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Inclusive upper bound. Null = no upper limit.',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    special_month_tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Tax in the rule set special_month (defaults to tax_amount when null).',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    sequence = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rule_set_id', 'sequence', 'salary_from']
        verbose_name = 'Professional Tax Slab'
        verbose_name_plural = 'Professional Tax Slabs'

    def __str__(self):
        upper = self.salary_to if self.salary_to is not None else '∞'
        return f'{self.rule_set.state_code} {self.salary_from}–{upper}: {self.tax_amount}'

    def clean(self):
        errors = {}
        if self.salary_to is not None and self.salary_from is not None:
            if self.salary_to < self.salary_from:
                errors['salary_to'] = 'salary_to must be on or after salary_from.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)

    def matches(self, wages: Decimal) -> bool:
        wages = Decimal(wages)
        if wages < Decimal(self.salary_from):
            return False
        if self.salary_to is not None and wages > Decimal(self.salary_to):
            return False
        return True

    def amount_for_month(self, *, month: int, special_month: int | None) -> Decimal:
        if special_month and month == special_month and self.special_month_tax_amount is not None:
            return Decimal(self.special_month_tax_amount)
        return Decimal(self.tax_amount)


class EmployeePTProfile(models.Model):
    """Per-employee PT jurisdiction (work state) and exemption flags.

    ``state_code`` is the PT work-state / jurisdiction — not the company
    registered address alone. Missing profile / blank state is treated as a
    validation gap (missing-work-state report), not a silent company fallback.
    """

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='pt_profile',
    )
    state_code = models.CharField(
        max_length=10,
        blank=True,
        help_text='PT jurisdiction / work state (e.g. AP). Required when is_applicable.',
    )
    is_applicable = models.BooleanField(default=True)
    exemption_type = models.CharField(
        max_length=30,
        choices=PTExemptionType.choices,
        blank=True,
        default='',
    )
    exemption_reason = models.CharField(max_length=255, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Inclusive end of this jurisdiction profile. Null = open-ended.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__employee_code']
        verbose_name = 'Employee PT Profile'
        verbose_name_plural = 'Employee PT Profiles'

    def __str__(self):
        return f'PT profile — {self.employee.employee_code} ({self.state_code or "no state"})'

    def clean(self):
        errors = {}
        if self.state_code:
            self.state_code = self.state_code.strip().upper()
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'effective_to must be on or after effective_from.'
        if self.is_applicable and not (self.state_code or '').strip():
            errors['state_code'] = (
                'PT work-state / jurisdiction is required when PT is applicable. '
                'Do not rely on company registered address alone.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.state_code:
            self.state_code = self.state_code.strip().upper()
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class PayrollPTResult(models.Model):
    """Immutable Professional Tax calculation snapshot linked to a payroll result."""

    payroll_result = models.OneToOneField(
        'payroll.PayrollResult',
        on_delete=models.CASCADE,
        related_name='pt_result',
    )
    rule_set = models.ForeignKey(
        ProfessionalTaxRuleSet,
        on_delete=models.PROTECT,
        related_name='payroll_pt_results',
        null=True,
        blank=True,
    )
    state_code = models.CharField(max_length=10, blank=True)
    pt_wages = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    exemption_reason = models.CharField(max_length=255, blank=True)
    calculation_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payroll_result_id']
        verbose_name = 'Payroll PT Result'
        verbose_name_plural = 'Payroll PT Results'

    def __str__(self):
        return f'PT result for payroll result #{self.payroll_result_id}'


# ---------------------------------------------------------------------------
# Income Tax / TDS (salaried) — documented seed rates (Sprint 9.4)
# ---------------------------------------------------------------------------
# Sources (approximate official structure for PAS seed data; always load from DB):
#   - Income-tax Act / Finance Acts — slab rates for OLD vs NEW regimes
#   - Budget 2024 (FY 2024-25) revised NEW regime slabs + std deduction ₹75,000;
#     rebate u/s 87A so that tax is nil up to taxable income ₹7,00,000 (NEW)
#   - Budget 2025 (FY 2025-26) further revised NEW regime slabs + rebate to
#     ₹12,00,000 taxable income (NEW); OLD regime slabs unchanged in seed
#   - Health & Education Cess: 4% on (tax + surcharge)
#   - Surcharge bands stored in ``surcharge_rules`` JSON (engine never hardcodes)
#
# OLD regime slabs (seed): 0–2.5L nil; 2.5–5L 5%; 5–10L 20%; above 10L 30%.
# Std deduction OLD: ₹50,000. Rebate 87A OLD: income ≤ ₹5,00,000.
#
# CRITICAL: Slabs / rates are NEVER hardcoded in the calculation engine —
# always load FinancialYearTaxRule + TaxSlab rows from the DB.
#
# Regime-change rule (payroll): employees may change tax regime for a FY until
# 31 July of that FY (e.g. FY 2024-25 → deadline 2024-07-31). After the
# deadline, the regime on the approved TaxDeclaration (else profile default
# effective at deadline) is locked for remaining payroll months of the FY.
# ---------------------------------------------------------------------------


class TaxRegime(models.TextChoices):
    OLD = 'OLD', 'Old regime'
    NEW = 'NEW', 'New regime'


class TaxResidency(models.TextChoices):
    RESIDENT = 'RESIDENT', 'Resident'
    NRI = 'NRI', 'Non-resident'
    RNOR = 'RNOR', 'Resident but not ordinarily resident'


class TaxDeclarationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED = 'APPROVED', 'Approved'


class InvestmentProofCategory(models.TextChoices):
    SECTION_80C = '80C', 'Section 80C'
    SECTION_80D = '80D', 'Section 80D'
    SECTION_80CCD = '80CCD', 'Section 80CCD'
    HRA = 'HRA', 'HRA exemption'
    HOUSING_LOAN = 'HOUSING_LOAN', 'Housing loan interest'
    OTHER = 'OTHER', 'Other deduction'


class FinancialYearTaxRule(models.Model):
    """Versioned income-tax rule set for one FY + regime. No overlapping dates."""

    financial_year = models.CharField(
        max_length=9,
        help_text='Indian FY label, e.g. 2024-25.',
        db_index=True,
    )
    tax_regime = models.CharField(max_length=10, choices=TaxRegime.choices)
    code = models.CharField(
        max_length=40,
        unique=True,
        help_text='Stable identifier snapshotted on payroll TDS results.',
    )
    name = models.CharField(max_length=120, blank=True)
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Inclusive end date. Null means open-ended.',
    )
    standard_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    rebate_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Section 87A: taxable income at/below this → full rebate of tax (before cess).',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    cess_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0400'),
        help_text='Health & Education Cess as a fraction (0.04 = 4%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    surcharge_rules = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Ordered list of {"income_from","income_to"|null,"rate"} bands. '
            'Rates are fractions (0.10 = 10%). Engine loads from DB only.'
        ),
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-financial_year', 'tax_regime', '-effective_from']
        verbose_name = 'Financial Year Tax Rule'
        verbose_name_plural = 'Financial Year Tax Rules'
        permissions = [
            ('export_tdsregister', 'Can export TDS registers'),
            ('export_form16', 'Can export Form 16 preparation data'),
        ]

    def __str__(self):
        end = self.effective_to or 'open'
        return f'{self.code} ({self.effective_from} – {end})'

    def clean(self):
        errors = {}
        if self.financial_year:
            self.financial_year = self.financial_year.strip()
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'effective_to must be on or after effective_from.'
        if self.effective_from and self.is_active and self.financial_year and self.tax_regime:
            overlap = self._overlapping_active_queryset()
            if overlap.exists():
                other = overlap.first()
                errors['__all__'] = (
                    f'Active date range overlaps {other.code} for '
                    f'{other.financial_year}/{other.tax_regime} '
                    f'({other.effective_from} – {other.effective_to or "open"}).'
                )
        if errors:
            raise ValidationError(errors)

    def _overlapping_active_queryset(self):
        start = self.effective_from
        end = self.effective_to
        qs = FinancialYearTaxRule.objects.filter(
            is_active=True,
            financial_year=self.financial_year,
            tax_regime=self.tax_regime,
        ).exclude(pk=self.pk)
        if end is None:
            qs = qs.filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start))
        else:
            qs = qs.filter(effective_from__lte=end).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=start)
            )
        return qs

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class TaxSlab(models.Model):
    """One taxable-income band within a FY tax rule. Rates come from DB only."""

    rule = models.ForeignKey(
        FinancialYearTaxRule,
        on_delete=models.CASCADE,
        related_name='slabs',
    )
    income_from = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Inclusive lower bound of annual taxable income.',
    )
    income_to = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Inclusive upper bound. Null = no upper limit.',
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Tax rate as a fraction (0.05 = 5%).',
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
    )
    sequence = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rule_id', 'sequence', 'income_from']
        verbose_name = 'Tax Slab'
        verbose_name_plural = 'Tax Slabs'

    def __str__(self):
        upper = self.income_to if self.income_to is not None else '∞'
        return f'{self.rule.code} {self.income_from}–{upper}: {self.rate}'

    def clean(self):
        errors = {}
        if self.income_to is not None and self.income_from is not None:
            if self.income_to < self.income_from:
                errors['income_to'] = 'income_to must be on or after income_from.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class EmployeeTaxProfile(models.Model):
    """Per-employee default tax regime, PAN, and residency."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='tax_profile',
    )
    default_tax_regime = models.CharField(
        max_length=10,
        choices=TaxRegime.choices,
        default=TaxRegime.NEW,
    )
    pan_number = models.CharField(
        max_length=10,
        blank=True,
        validators=[validate_pan],
    )
    tax_residency = models.CharField(
        max_length=20,
        choices=TaxResidency.choices,
        default=TaxResidency.RESIDENT,
    )
    effective_from = models.DateField(null=True, blank=True)
    is_tds_applicable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__employee_code']
        verbose_name = 'Employee Tax Profile'
        verbose_name_plural = 'Employee Tax Profiles'

    def __str__(self):
        return f'Tax profile — {self.employee.employee_code} ({self.default_tax_regime})'

    def clean(self):
        errors = {}
        if self.pan_number:
            try:
                validate_pan(self.pan_number)
            except ValidationError as exc:
                errors['pan_number'] = exc.messages
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pan_number:
            self.pan_number = self.pan_number.strip().upper()
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class TaxDeclaration(models.Model):
    """Employee investment / deduction declaration for one financial year."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='tax_declarations',
    )
    financial_year = models.CharField(max_length=9, db_index=True)
    regime = models.CharField(max_length=10, choices=TaxRegime.choices)
    declared_amounts = models.JSONField(
        default=dict,
        blank=True,
        help_text='Flexible map of deduction codes → amounts (e.g. {"80C": "150000"}).',
    )
    section_80c = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    section_80d = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    housing_loan = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Interest on housing loan (e.g. u/s 24).',
    )
    hra = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Claimed HRA exemption amount.',
    )
    other_deductions = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    status = models.CharField(
        max_length=20,
        choices=TaxDeclarationStatus.choices,
        default=TaxDeclarationStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-financial_year', 'employee__employee_code']
        verbose_name = 'Tax Declaration'
        verbose_name_plural = 'Tax Declarations'
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'financial_year'],
                name='uniq_tax_declaration_employee_fy',
            ),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} {self.financial_year} ({self.regime}/{self.status})'

    def total_old_regime_deductions(self) -> Decimal:
        """Sum structured + JSON declared amounts (for OLD regime projection)."""
        total = (
            Decimal(self.section_80c or 0)
            + Decimal(self.section_80d or 0)
            + Decimal(self.housing_loan or 0)
            + Decimal(self.hra or 0)
            + Decimal(self.other_deductions or 0)
        )
        extras = self.declared_amounts or {}
        for key, value in extras.items():
            if key in {'80C', '80D', 'HOUSING_LOAN', 'HRA', 'OTHER'}:
                continue  # already in structured fields when mirrored
            try:
                total += Decimal(str(value))
            except Exception:  # noqa: BLE001
                continue
        return total


class InvestmentProof(models.Model):
    """Supporting proof for a tax declaration (or employee+FY)."""

    declaration = models.ForeignKey(
        TaxDeclaration,
        on_delete=models.CASCADE,
        related_name='proofs',
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='investment_proofs',
        null=True,
        blank=True,
    )
    financial_year = models.CharField(max_length=9, blank=True)
    category = models.CharField(
        max_length=20,
        choices=InvestmentProofCategory.choices,
        default=InvestmentProofCategory.OTHER,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    proof_file = models.FileField(
        upload_to='compliance/investment_proofs/',
        blank=True,
        null=True,
    )
    verified = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Investment Proof'
        verbose_name_plural = 'Investment Proofs'

    def __str__(self):
        return f'{self.category} {self.amount} ({self.financial_year or "—"})'

    def clean(self):
        errors = {}
        if self.declaration_id is None and self.employee_id is None:
            errors['__all__'] = 'Either declaration or employee must be set.'
        if self.declaration_id and not self.financial_year:
            self.financial_year = self.declaration.financial_year
        if self.declaration_id and self.employee_id is None:
            self.employee = self.declaration.employee
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.declaration_id:
            if not self.financial_year:
                self.financial_year = self.declaration.financial_year
            if self.employee_id is None:
                self.employee = self.declaration.employee
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class PreviousEmployerIncome(models.Model):
    """Income / TDS from previous employer(s) for mid-year joins."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='previous_employer_incomes',
    )
    financial_year = models.CharField(max_length=9, db_index=True)
    employer_name = models.CharField(max_length=200, blank=True)
    taxable_income = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    tds_deducted = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    pf_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    professional_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-financial_year', 'employee__employee_code']
        verbose_name = 'Previous Employer Income'
        verbose_name_plural = 'Previous Employer Incomes'

    def __str__(self):
        return (
            f'{self.employee.employee_code} {self.financial_year} '
            f'income={self.taxable_income} tds={self.tds_deducted}'
        )


class PayrollTDSResult(models.Model):
    """Immutable TDS calculation snapshot linked to a payroll result."""

    payroll_result = models.OneToOneField(
        'payroll.PayrollResult',
        on_delete=models.CASCADE,
        related_name='tds_result',
    )
    rule_set = models.ForeignKey(
        FinancialYearTaxRule,
        on_delete=models.PROTECT,
        related_name='payroll_tds_results',
        null=True,
        blank=True,
    )
    financial_year = models.CharField(max_length=9, blank=True)
    tax_regime = models.CharField(max_length=10, blank=True)
    taxable_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Projected annual taxable income used for slab calculation.',
    )
    annual_tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total annual tax liability including surcharge and cess.',
    )
    monthly_tds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    tax_before_cess = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    surcharge = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    cess = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    rebate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    relief = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Reserved for u/s 89 relief; default zero.',
    )
    previous_tds = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='YTD payroll TDS + previous employer TDS already recovered.',
    )
    calculation_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payroll_result_id']
        verbose_name = 'Payroll TDS Result'
        verbose_name_plural = 'Payroll TDS Results'

    def __str__(self):
        return f'TDS result for payroll result #{self.payroll_result_id}'
