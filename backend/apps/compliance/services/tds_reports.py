"""TDS register / summary reports from snapshots (Sprint 9.4)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollTDSResult
from apps.payroll.models import PayrollRun


def workbook_response(workbook: Workbook, filename: str) -> HttpResponse:
    stream = BytesIO()
    workbook.save(stream)
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _workbook(title: str, headers: list[str]):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    return wb, ws


def _tds_qs(run: PayrollRun):
    return (
        PayrollTDSResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )


def export_tds_register(run: PayrollRun) -> HttpResponse:
    headers = [
        'Emp Code', 'Name', 'FY', 'Regime', 'Rule', 'Taxable Income',
        'Annual Tax', 'Monthly TDS', 'Cess', 'Rebate', 'Surcharge', 'Previous TDS',
    ]
    wb, ws = _workbook('TDS Register', headers)
    for row in _tds_qs(run):
        emp = row.payroll_result.employee
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            row.financial_year,
            row.tax_regime,
            row.rule_set.code if row.rule_set_id else '',
            row.taxable_salary,
            row.annual_tax,
            row.monthly_tds,
            row.cess,
            row.rebate,
            row.surcharge,
            row.previous_tds,
        ])
    return workbook_response(wb, f'tds_register_run_{run.pk}.xlsx')


def export_tds_monthly_summary(run: PayrollRun) -> HttpResponse:
    headers = ['Metric', 'Amount']
    wb, ws = _workbook('Monthly TDS Summary', headers)
    qs = list(_tds_qs(run))
    taxed = [r for r in qs if Decimal(r.monthly_tds) > 0]
    by_regime: dict[str, Decimal] = {}
    for r in qs:
        key = r.tax_regime or '(none)'
        by_regime[key] = by_regime.get(key, Decimal('0.00')) + Decimal(r.monthly_tds)
    totals = {
        'Employees (all)': len(qs),
        'Employees (TDS > 0)': len(taxed),
        'Total Monthly TDS': sum((r.monthly_tds for r in qs), Decimal('0.00')),
        'Total Annual Tax (projected)': sum((r.annual_tax for r in qs), Decimal('0.00')),
        'Total Cess': sum((r.cess for r in qs), Decimal('0.00')),
        'Total Rebate': sum((r.rebate for r in qs), Decimal('0.00')),
    }
    for key, value in totals.items():
        ws.append([key, value])
    ws.append([])
    ws.append(['Regime', 'Monthly TDS'])
    for regime, amount in sorted(by_regime.items()):
        ws.append([regime, amount])
    return workbook_response(wb, f'tds_monthly_summary_run_{run.pk}.xlsx')


def export_missing_pan(run: PayrollRun) -> HttpResponse:
    headers = ['Emp Code', 'Name', 'Regime', 'Monthly TDS', 'Note']
    wb, ws = _workbook('Missing PAN', headers)
    for row in _tds_qs(run):
        emp = row.payroll_result.employee
        pan = ''
        try:
            pan = (emp.tax_profile.pan_number or '').strip()
        except Exception:  # noqa: BLE001
            pan = ''
        if pan:
            continue
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            row.tax_regime,
            row.monthly_tds,
            'PAN missing on EmployeeTaxProfile',
        ])
    return workbook_response(wb, f'tds_missing_pan_run_{run.pk}.xlsx')


TDS_REPORT_EXPORTS = {
    'tds_register': export_tds_register,
    'tds_monthly_summary': export_tds_monthly_summary,
    'missing_pan': export_missing_pan,
}
