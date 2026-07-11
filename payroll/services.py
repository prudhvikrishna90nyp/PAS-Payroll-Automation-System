from decimal import Decimal

from django.db import transaction

from employee.models import Employee
from .models import PayPeriod, Payslip, PayslipItem


def calculate_payslip_amounts(employee, pay_period):
    basic = employee.basic_salary
    hra = (basic * Decimal('0.40')).quantize(Decimal('0.01'))
    transport = Decimal('1600.00')
    gross = basic + hra + transport
    pf = (basic * Decimal('0.12')).quantize(Decimal('0.01'))
    tax = Decimal('0.00')
    if gross > Decimal('50000.00'):
        tax = ((gross - Decimal('50000.00')) * Decimal('0.10')).quantize(Decimal('0.01'))
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

    gross, total_deductions, net_pay, earnings, deductions = calculate_payslip_amounts(
        employee,
        pay_period,
    )
    payslip.basic_salary = employee.basic_salary
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


def generate_payslips_for_period(pay_period):
    employees = Employee.objects.filter(is_active=True)
    return [generate_payslip(employee, pay_period) for employee in employees]
