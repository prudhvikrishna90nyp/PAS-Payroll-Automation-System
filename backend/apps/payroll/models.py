from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from apps.common.mixins import SoftDeleteModel
from apps.company.models import Company
from apps.employee.models import Employee


class PayPeriod(models.Model):
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = 'employees_payperiod'
        ordering = ['-year', '-month']
        unique_together = [['year', 'month']]

    def __str__(self):
        return f'{self.year}-{self.month:02d}'


class Payslip(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        FINALIZED = 'finalized', 'Finalized'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payslips',
    )
    pay_period = models.ForeignKey(
        PayPeriod,
        on_delete=models.CASCADE,
        related_name='payslips',
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employees_payslip'
        ordering = ['-pay_period__year', '-pay_period__month', 'employee__employee_code']
        unique_together = [['employee', 'pay_period']]

    def __str__(self):
        return f'{self.employee.employee_code} - {self.pay_period}'


class PayslipItem(models.Model):
    class ItemType(models.TextChoices):
        EARNING = 'earning', 'Earning'
        DEDUCTION = 'deduction', 'Deduction'

    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name='items',
    )
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        db_table = 'employees_payslipitem'
        ordering = ['item_type', 'description']

    def __str__(self):
        return f'{self.description}: {self.amount}'


class ComponentType(models.TextChoices):
    EARNING = 'earning', 'Earning'
    DEDUCTION = 'deduction', 'Deduction'
    EMPLOYER_CONTRIBUTION = 'employer_contribution', 'Employer Contribution'


class CalculationType(models.TextChoices):
    FIXED = 'fixed', 'Fixed'
    PERCENTAGE = 'percentage', 'Percentage'
    FORMULA = 'formula', 'Formula'


class RoundingRule(models.TextChoices):
    NONE = 'none', 'None'
    NEAREST = 'nearest', 'Nearest Rupee'
    ROUND_UP = 'round_up', 'Round Up'
    ROUND_DOWN = 'round_down', 'Round Down'


class SalaryComponent(SoftDeleteModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='salary_components',
    )
    component_code = models.CharField(max_length=30)
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=30, choices=ComponentType.choices)
    calculation_type = models.CharField(
        max_length=20,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
    )
    formula = models.CharField(max_length=500, blank=True)
    taxable = models.BooleanField(default=True)
    pf_applicable = models.BooleanField(default=False)
    esi_applicable = models.BooleanField(default=False)
    include_in_ctc = models.BooleanField(default=True)
    include_in_gross = models.BooleanField(default=True)
    rounding_rule = models.CharField(
        max_length=20,
        choices=RoundingRule.choices,
        default=RoundingRule.NEAREST,
    )
    display_order = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salarycomponent_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salarycomponent_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['company__company_name', 'display_order', 'component_code']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'component_code'],
                condition=models.Q(is_deleted=False),
                name='uniq_salarycomponent_company_code_alive',
            ),
        ]
        permissions = [
            ('export_salarycomponent', 'Can export salary component register'),
        ]

    def __str__(self):
        return f'{self.component_code} — {self.component_name}'

    def get_absolute_url(self):
        return reverse('payroll:component_detail', kwargs={'pk': self.pk})

    def clean(self):
        errors = {}
        if self.calculation_type == CalculationType.FORMULA and not (self.formula or '').strip():
            errors['formula'] = 'Formula is required when calculation type is Formula.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.component_code = self.component_code.strip().upper()
        self.component_name = self.component_name.strip()
        if self.formula:
            self.formula = self.formula.strip()
        super().save(*args, **kwargs)


class SalaryStructure(SoftDeleteModel):
    """Component-based salary structure (payroll master). Distinct from employee.SalaryStructure."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='payroll_salary_structures',
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salarystructure_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salarystructure_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['company__company_name', 'name']
        verbose_name = 'Salary Structure'
        verbose_name_plural = 'Salary Structures'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code'],
                condition=models.Q(is_deleted=False),
                name='uniq_payroll_salarystructure_company_code_alive',
            ),
        ]
        permissions = [
            ('export_salarystructure', 'Can export salary structure register'),
        ]

    def __str__(self):
        return f'{self.company.company_name} — {self.name}'

    def get_absolute_url(self):
        return reverse('payroll:structure_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class SalaryStructureLine(models.Model):
    structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name='structure_lines',
    )
    calculation_type = models.CharField(
        max_length=20,
        choices=CalculationType.choices,
        blank=True,
        help_text='Leave blank to use the component default.',
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Fixed amount when calculation type is Fixed.',
    )
    percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Percentage value when calculation type is Percentage.',
    )
    formula_override = models.CharField(max_length=500, blank=True)
    display_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['display_order', 'component__component_code']
        verbose_name = 'Salary Structure Line'
        verbose_name_plural = 'Salary Structure Lines'
        constraints = [
            models.UniqueConstraint(
                fields=['structure', 'component'],
                name='uniq_structure_line_component',
            ),
        ]

    def __str__(self):
        return f'{self.structure.code} / {self.component.component_code}'

    @property
    def effective_calculation_type(self):
        return self.calculation_type or self.component.calculation_type

    @property
    def effective_formula(self):
        return (self.formula_override or self.component.formula or '').strip()

    def clean(self):
        errors = {}
        if self.structure_id and self.component_id:
            if self.structure.company_id != self.component.company_id:
                errors['component'] = 'Component must belong to the same company as the structure.'
        calc = self.effective_calculation_type
        if calc == CalculationType.FIXED and self.value is None:
            errors['value'] = 'Value is required for fixed calculation.'
        if calc == CalculationType.PERCENTAGE and self.percent is None:
            errors['percent'] = 'Percent is required for percentage calculation.'
        if calc == CalculationType.FORMULA and not self.effective_formula:
            errors['formula_override'] = 'Formula is required for formula calculation.'
        if self.percent is not None and (self.percent < 0 or self.percent > 1000):
            errors['percent'] = 'Percent must be between 0 and 1000.'
        if errors:
            raise ValidationError(errors)


class EmployeeSalaryAssignment(SoftDeleteModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salary_assignments',
    )
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.PROTECT,
        related_name='assignments',
    )
    effective_from = models.DateField()
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Null means currently active.',
    )
    gross_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    ctc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Annual CTC; leave 0 to auto-calculate from monthly figures.',
    )
    remarks = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salaryassignment_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_salaryassignment_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-effective_from', '-id']
        verbose_name = 'Employee Salary Assignment'
        verbose_name_plural = 'Employee Salary Assignments'
        permissions = [
            ('export_employeesalaryassignment', 'Can export employee salary register'),
        ]

    def __str__(self):
        return (
            f'{self.employee.employee_code} / {self.salary_structure.code} '
            f'from {self.effective_from}'
        )

    def get_absolute_url(self):
        return reverse('payroll:assignment_detail', kwargs={'pk': self.pk})

    @property
    def is_current(self):
        return self.effective_to is None and self.is_active and not self.is_deleted

    def clean(self):
        errors = {}
        if self.employee_id and self.salary_structure_id:
            if self.employee.company_id != self.salary_structure.company_id:
                errors['salary_structure'] = (
                    'Salary structure must belong to the employee company.'
                )
        if self.gross_salary is not None and self.gross_salary < 0:
            errors['gross_salary'] = 'Gross salary cannot be negative.'
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            errors['effective_to'] = 'Effective to cannot be before effective from.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        sync_employee = kwargs.pop('sync_employee', True)
        close_previous = kwargs.pop('close_previous', True)
        with transaction.atomic():
            if close_previous and self.effective_to is None and self.employee_id:
                previous = (
                    EmployeeSalaryAssignment.objects
                    .filter(employee_id=self.employee_id, effective_to__isnull=True)
                    .exclude(pk=self.pk)
                )
                for prior in previous:
                    prior.effective_to = self.effective_from - timedelta(days=1)
                    prior.save(update_fields=['effective_to', 'updated_at'])
            super().save(*args, **kwargs)
            if sync_employee:
                self._sync_employee_basic()

    def _sync_employee_basic(self):
        """Keep Employee.basic_salary aligned for legacy payslip generation."""
        from .services.salary_calculator import calculate_assignment_components

        if not self.is_current:
            return
        try:
            result = calculate_assignment_components(self)
            basic = result.amounts.get('BASIC') or result.amounts.get('Basic')
            if basic is None:
                for code, amount in result.amounts.items():
                    if code.upper() == 'BASIC':
                        basic = amount
                        break
            if basic is not None:
                Employee.objects.filter(pk=self.employee_id).update(basic_salary=basic)
        except Exception:
            # Assignment remains valid even if formula preview fails.
            pass


# ---------------------------------------------------------------------------
# Payroll engine foundation (Sprint 8.1 / v0.8.1)
# Source of truth for company periods and runs going forward.
# Legacy PayPeriod / Payslip remain for existing payslip generation until
# payslip wiring is migrated in a later sprint.
# ---------------------------------------------------------------------------


class PayrollPeriodStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'


class PayrollRunStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    CALCULATED = 'calculated', 'Calculated'
    INCOMPLETE = 'incomplete', 'Incomplete'
    REVIEWED = 'reviewed', 'Reviewed'
    APPROVED = 'approved', 'Approved'
    LOCKED = 'locked', 'Locked'


class PayrollPeriod(models.Model):
    """Company payroll calendar period. Prefer this over legacy PayPeriod."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='payroll_periods',
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=PayrollPeriodStatus.choices,
        default=PayrollPeriodStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_period_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_period_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-year', '-month', 'company__company_name']
        verbose_name = 'Payroll Period'
        verbose_name_plural = 'Payroll Periods'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'month', 'year'],
                name='uniq_payroll_period_company_month_year',
            ),
        ]

    def __str__(self):
        return (
            f'{self.company.company_name} — {self.month:02d}/{self.year} '
            f'({self.get_status_display()})'
        )

    def get_absolute_url(self):
        return reverse('payroll:period_detail', kwargs={'pk': self.pk})

    @property
    def is_open(self):
        return self.status == PayrollPeriodStatus.OPEN

    def clean(self):
        errors = {}
        if self.month is not None and (self.month < 1 or self.month > 12):
            errors['month'] = 'Month must be between 1 and 12.'
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors['end_date'] = 'End date must be on or after start date.'
        if self.company_id and self.start_date and self.end_date:
            overlap = (
                PayrollPeriod.objects
                .filter(company_id=self.company_id)
                .exclude(pk=self.pk)
                .filter(start_date__lte=self.end_date, end_date__gte=self.start_date)
            )
            if overlap.exists():
                other = overlap.first()
                errors['__all__'] = (
                    f'Date range overlaps existing period '
                    f'{other.month:02d}/{other.year} '
                    f'({other.start_date} – {other.end_date}).'
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Skip full_clean when only status/audit fields change (open/close).
        if kwargs.get('update_fields') is None:
            self.full_clean()
        super().save(*args, **kwargs)


class PayrollRun(models.Model):
    """Versioned payroll processing run for a company period."""

    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='runs',
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='payroll_runs',
    )
    run_number = models.PositiveIntegerField(
        default=1,
        help_text='Version number within the period (1, 2, …).',
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollRunStatus.choices,
        default=PayrollRunStatus.DRAFT,
    )
    notes = models.TextField(blank=True)
    pf_rule_set = models.ForeignKey(
        'compliance.PFRuleSet',
        on_delete=models.PROTECT,
        related_name='payroll_runs',
        null=True,
        blank=True,
        help_text='PF rule set snapshotted at calculation time (immutable historical rates).',
    )
    esi_rule_set = models.ForeignKey(
        'compliance.ESIRuleSet',
        on_delete=models.PROTECT,
        related_name='payroll_runs',
        null=True,
        blank=True,
        help_text='ESI rule set snapshotted at calculation time (immutable historical rates).',
    )
    calculation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text='Per-employee calculation errors from the last calculate_run().',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_runs_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-run_number']
        verbose_name = 'Payroll Run'
        verbose_name_plural = 'Payroll Runs'
        constraints = [
            models.UniqueConstraint(
                fields=['period', 'run_number'],
                name='uniq_payroll_run_period_number',
            ),
        ]
        permissions = [
            ('review_payrollrun', 'Can review payroll run'),
            ('approve_payrollrun', 'Can approve payroll run'),
            ('lock_payrollrun', 'Can lock payroll run'),
        ]

    def __str__(self):
        return f'{self.company.company_name} run #{self.run_number} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('payroll:run_detail', kwargs={'pk': self.pk})

    @property
    def is_locked(self):
        return self.status == PayrollRunStatus.LOCKED

    @property
    def is_calculable(self):
        """Draft / Calculated / Incomplete (unlocked) runs may be calculated."""
        return self.status in {
            PayrollRunStatus.DRAFT,
            PayrollRunStatus.CALCULATED,
            PayrollRunStatus.INCOMPLETE,
        }

    @property
    def has_calculation_errors(self):
        return bool(self.calculation_errors)

    def clean(self):
        errors = {}
        if self.period_id and self.company_id and self.period.company_id != self.company_id:
            errors['company'] = 'Company must match the payroll period company.'
        if self.period_id and self.period.status == PayrollPeriodStatus.CLOSED:
            if not self.pk:
                errors['period'] = 'Cannot create a run for a closed payroll period.'
        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        if self.pk:
            locked = (
                PayrollRun.objects
                .filter(pk=self.pk, status=PayrollRunStatus.LOCKED)
                .exists()
            )
            if locked:
                raise ValidationError('Cannot delete a locked payroll run.')
        return super().delete(*args, **kwargs)


class PayrollResult(models.Model):
    """Per-employee snapshot for a payroll run. Immutable intent when run is locked."""

    run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='results',
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payroll_results',
    )
    present_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    absent_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    lop_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    total_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    ctc_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Optional CTC snapshot at calculation time.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__employee_code']
        verbose_name = 'Payroll Result'
        verbose_name_plural = 'Payroll Results'
        constraints = [
            models.UniqueConstraint(
                fields=['run', 'employee'],
                name='uniq_payroll_result_run_employee',
            ),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} @ run #{self.run.run_number}'

    def clean(self):
        if self.pk and self.run_id:
            if PayrollRun.objects.filter(pk=self.run_id, status=PayrollRunStatus.LOCKED).exists():
                raise ValidationError('Cannot modify payroll results after the run is locked.')

    def save(self, *args, **kwargs):
        if self.pk and self.run_id:
            if PayrollRun.objects.filter(pk=self.run_id, status=PayrollRunStatus.LOCKED).exists():
                raise ValidationError('Cannot modify payroll results after the run is locked.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.run_id and PayrollRun.objects.filter(
            pk=self.run_id, status=PayrollRunStatus.LOCKED
        ).exists():
            raise ValidationError('Cannot delete payroll results after the run is locked.')
        return super().delete(*args, **kwargs)


class PayrollResultComponent(models.Model):
    """Line-level earning/deduction component on a payroll result."""

    result = models.ForeignKey(
        PayrollResult,
        on_delete=models.CASCADE,
        related_name='components',
    )
    component_code = models.CharField(max_length=30)
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=30, choices=ComponentType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    calculation_detail = models.JSONField(
        default=dict,
        blank=True,
        help_text='Formula inputs, rates, or other calculation metadata.',
    )

    class Meta:
        ordering = ['component_type', 'component_code']
        verbose_name = 'Payroll Result Component'
        verbose_name_plural = 'Payroll Result Components'

    def __str__(self):
        return f'{self.component_code}: {self.amount}'

    def _run_is_locked(self) -> bool:
        if not self.result_id:
            return False
        return PayrollRun.objects.filter(
            results__pk=self.result_id,
            status=PayrollRunStatus.LOCKED,
        ).exists()

    def save(self, *args, **kwargs):
        if self.pk and self._run_is_locked():
            raise ValidationError(
                'Cannot modify payroll result components after the run is locked.'
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self._run_is_locked():
            raise ValidationError(
                'Cannot delete payroll result components after the run is locked.'
            )
        return super().delete(*args, **kwargs)


class PayrollAuditLog(models.Model):
    """Audit trail for period and run lifecycle actions."""

    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=50)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payroll_audit_logs',
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Payroll Audit Log'
        verbose_name_plural = 'Payroll Audit Logs'

    def __str__(self):
        return f'{self.action} @ {self.timestamp:%Y-%m-%d %H:%M}'
