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
