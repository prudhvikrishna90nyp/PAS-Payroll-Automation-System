"""EPF / statutory compliance models (Sprint 9.1)."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.validators import validate_uan
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
