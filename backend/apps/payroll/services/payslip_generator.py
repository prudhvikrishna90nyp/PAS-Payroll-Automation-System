"""Payslip generation — wraps legacy calculation; structure-aware path when assigned."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.employee.models import Employee

from ..models import ComponentType, EmployeeSalaryAssignment, PayPeriod, Payslip, PayslipItem
from .salary_calculator import calculate_assignment_components
from .statutory import calculate_employee_pf, calculate_tds


def _legacy_calculate_payslip_amounts(employee, pay_period):
    """Original hardcoded Indian-style breakdown (pre component engine)."""
    _ = pay_period
    basic = employee.basic_salary
    hra = (basic * Decimal('0.40')).quantize(Decimal('0.01'))
    transport = Decimal('1600.00')
    gross = basic + hra + transport
    pf = calculate_employee_pf(basic)
    tax = calculate_tds(gross)
    total_deductions = pf + tax
    net_pay = gross - total_deductions

    earnings = [
        ('Basic Salary', basic),
        ('House Rent Allowance', hra),
        ('Transport Allowance', transport),
    ]
    deductions = [
        ('Provident Fund', pf),
        ('Income Tax (TDS)', tax),
    ]
    return gross, total_deductions, net_pay, earnings, deductions, basic


def _current_assignment(employee: Employee, on_date=None) -> EmployeeSalaryAssignment | None:
    from django.db.models import Q

    on_date = on_date or timezone.localdate()
    return (
        EmployeeSalaryAssignment.objects
        .filter(employee=employee, is_active=True, effective_from__lte=on_date)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
        .select_related('salary_structure')
        .order_by('-effective_from', '-id')
        .first()
    )


def _structure_calculate_payslip_amounts(assignment: EmployeeSalaryAssignment):
    result = calculate_assignment_components(assignment)
    earnings = []
    deductions = []
    basic = Decimal('0.00')
    for row in result.lines:
        amount = row['amount']
        if amount <= 0:
            continue
        label = row['component_name']
        if row['component_type'] == ComponentType.EARNING:
            earnings.append((label, amount))
            if row['component_code'].upper() == 'BASIC':
                basic = amount
        elif row['component_type'] == ComponentType.DEDUCTION:
            deductions.append((label, amount))

    # If structure has no deductions, keep PF/TDS stubs for continuity
    if not deductions:
        pf = calculate_employee_pf(basic or assignment.gross_salary)
        tax = calculate_tds(result.gross)
        if pf > 0:
            deductions.append(('Provident Fund', pf))
        if tax > 0:
            deductions.append(('Income Tax (TDS)', tax))

    total_deductions = sum((amt for _, amt in deductions), Decimal('0.00'))
    earnings_total = sum((amt for _, amt in earnings), Decimal('0.00'))
    gross = result.gross if result.gross else earnings_total
    net_pay = gross - total_deductions
    if basic <= 0:
        basic = assignment.employee.basic_salary
    return gross, total_deductions, net_pay, earnings, deductions, basic


def calculate_payslip_amounts(employee, pay_period):
    """
    Public API used by views/tests.

    Prefers active EmployeeSalaryAssignment + structure calculator when present;
    otherwise falls back to the legacy hardcoded breakdown.
    """
    on_date = getattr(pay_period, 'end_date', None) or timezone.localdate()
    assignment = _current_assignment(employee, on_date=on_date)
    if assignment is not None and assignment.salary_structure.lines.exists():
        gross, total_deductions, net_pay, earnings, deductions, _basic = (
            _structure_calculate_payslip_amounts(assignment)
        )
        return gross, total_deductions, net_pay, earnings, deductions

    gross, total_deductions, net_pay, earnings, deductions, _basic = (
        _legacy_calculate_payslip_amounts(employee, pay_period)
    )
    return gross, total_deductions, net_pay, earnings, deductions


@transaction.atomic
def generate_payslip(employee, pay_period):
    payslip, created = Payslip.objects.get_or_create(
        employee=employee,
        pay_period=pay_period,
        defaults={
            'basic_salary': employee.basic_salary,
            'gross_pay': Decimal('0.00'),
            'total_deductions': Decimal('0.00'),
            'net_pay': Decimal('0.00'),
        },
    )
    if not created and payslip.status == Payslip.Status.FINALIZED:
        return payslip

    on_date = getattr(pay_period, 'end_date', None) or timezone.localdate()
    assignment = _current_assignment(employee, on_date=on_date)
    if assignment is not None and assignment.salary_structure.lines.exists():
        gross, total_deductions, net_pay, earnings, deductions, basic = (
            _structure_calculate_payslip_amounts(assignment)
        )
    else:
        gross, total_deductions, net_pay, earnings, deductions, basic = (
            _legacy_calculate_payslip_amounts(employee, pay_period)
        )

    payslip.basic_salary = basic
    payslip.gross_pay = gross
    payslip.total_deductions = total_deductions
    payslip.net_pay = net_pay
    payslip.save()

    payslip.items.all().delete()
    for description, amount in earnings:
        PayslipItem.objects.create(
            payslip=payslip,
            item_type=PayslipItem.ItemType.EARNING,
            description=description,
            amount=amount,
        )
    for description, amount in deductions:
        if amount > 0:
            PayslipItem.objects.create(
                payslip=payslip,
                item_type=PayslipItem.ItemType.DEDUCTION,
                description=description,
                amount=amount,
            )
    return payslip


def generate_payslips_for_period(pay_period: PayPeriod):
    employees = Employee.objects.filter(is_active=True)
    return [generate_payslip(employee, pay_period) for employee in employees]
