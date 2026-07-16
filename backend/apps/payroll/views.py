from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from .models import PayPeriod, Payslip
from .services import generate_payslips_for_period


def payslip_list(request):
    pay_periods = PayPeriod.objects.all()
    selected_period_id = request.GET.get('period')
    payslips = Payslip.objects.select_related('employee', 'pay_period')

    if selected_period_id:
        payslips = payslips.filter(pay_period_id=selected_period_id)

    return render(
        request,
        'payroll/payslip_list.html',
        {
            'payslips': payslips,
            'pay_periods': pay_periods,
            'selected_period_id': int(selected_period_id) if selected_period_id else None,
        },
    )


def payslip_detail(request, pk):
    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'pay_period').prefetch_related('items'),
        pk=pk,
    )
    earnings = payslip.items.filter(item_type='earning')
    deductions = payslip.items.filter(item_type='deduction')
    return render(
        request,
        'payroll/payslip_detail.html',
        {
            'payslip': payslip,
            'earnings': earnings,
            'deductions': deductions,
        },
    )


def payslip_pdf(request, pk):
    try:
        from weasyprint import HTML
    except OSError:
        return HttpResponse(
            'PDF generation requires WeasyPrint system libraries. '
            'On Windows, install GTK3 runtime: '
            'https://doc.courtbouillon.org/weasyprint/stable/first_steps.html',
            status=503,
        )

    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'pay_period').prefetch_related('items'),
        pk=pk,
    )
    html = render_to_string(
        'payroll/payslip_pdf.html',
        {
            'payslip': payslip,
            'earnings': payslip.items.filter(item_type='earning'),
            'deductions': payslip.items.filter(item_type='deduction'),
        },
    )
    pdf = HTML(string=html).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'payslip_{payslip.employee.employee_id}_{payslip.pay_period}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def payslip_export_excel(request):
    period_id = request.GET.get('period')
    payslips = Payslip.objects.select_related('employee', 'pay_period')
    if period_id:
        payslips = payslips.filter(pay_period_id=period_id)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Payslips'
    sheet.append([
        'Employee ID',
        'Employee Name',
        'Pay Period',
        'Basic Salary',
        'Gross Pay',
        'Deductions',
        'Net Pay',
        'Status',
    ])
    for payslip in payslips:
        sheet.append([
            payslip.employee.employee_id,
            payslip.employee.full_name,
            str(payslip.pay_period),
            float(payslip.basic_salary),
            float(payslip.gross_pay),
            float(payslip.total_deductions),
            float(payslip.net_pay),
            payslip.get_status_display(),
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="payslips.xlsx"'
    return response


@require_POST
def generate_period_payslips(request, period_id):
    pay_period = get_object_or_404(PayPeriod, pk=period_id)
    generate_payslips_for_period(pay_period)
    return redirect(f'{request.META.get("HTTP_REFERER", "/payroll/payslips/")}')
