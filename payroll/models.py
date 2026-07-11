from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from employee.models import Employee


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
        ordering = ['-pay_period__year', '-pay_period__month', 'employee__employee_id']
        unique_together = [['employee', 'pay_period']]

    def __str__(self):
        return f'{self.employee.employee_id} - {self.pay_period}'


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
