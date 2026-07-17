"""PT register and summary Excel reports (Sprint 9.3).

Reports reconcile from immutable ``PayrollPTResult`` snapshots only.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollPTResult
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


def _pt_qs(run: PayrollRun):
    return (
        PayrollPTResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )


def export_pt_register(run: PayrollRun) -> HttpResponse:
    headers = [
        'Emp Code', 'Name', 'State', 'Rule', 'PT Wages', 'Tax Amount',
        'Exemption Reason', 'Special Month', 'Missing Work State',
    ]
    wb, ws = _workbook('PT Register', headers)
    for pt in _pt_qs(run):
        emp = pt.payroll_result.employee
        snap = pt.calculation_snapshot or {}
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            pt.state_code,
            pt.rule_set.name if pt.rule_set_id else '',
            pt.pt_wages,
            pt.tax_amount,
            pt.exemption_reason,
            'Yes' if snap.get('special_month_applied') else 'No',
            'Yes' if snap.get('missing_work_state') else 'No',
        ])
    return workbook_response(wb, f'pt_register_run_{run.pk}.xlsx')


def export_pt_monthly_summary(run: PayrollRun) -> HttpResponse:
    headers = ['Metric', 'Amount']
    wb, ws = _workbook('Monthly PT Summary', headers)
    qs = list(_pt_qs(run))
    taxed = [p for p in qs if Decimal(p.tax_amount) > 0]
    missing = [p for p in qs if (p.calculation_snapshot or {}).get('missing_work_state')]
    exempt = [p for p in qs if p.exemption_reason and Decimal(p.tax_amount) == 0]
    by_state: dict[str, Decimal] = {}
    for p in qs:
        key = p.state_code or '(none)'
        by_state[key] = by_state.get(key, Decimal('0.00')) + Decimal(p.tax_amount)
    totals = {
        'Employees (all)': len(qs),
        'Employees (taxed)': len(taxed),
        'Employees (exempt / zero)': len(exempt),
        'Missing work state': len(missing),
        'PT Wages (taxed)': sum((p.pt_wages for p in taxed), Decimal('0.00')),
        'Total PT': sum((p.tax_amount for p in qs), Decimal('0.00')),
    }
    for key, value in totals.items():
        ws.append([key, value])
    ws.append([])
    ws.append(['State', 'Tax Amount'])
    for state, amount in sorted(by_state.items()):
        ws.append([state, amount])
    return workbook_response(wb, f'pt_monthly_summary_run_{run.pk}.xlsx')


def export_missing_pt_work_state(run: PayrollRun) -> HttpResponse:
    """Employees missing PT work-state / jurisdiction (never silent)."""
    headers = ['Emp Code', 'Name', 'State', 'Applicable Tax', 'Exemption / Notes']
    wb, ws = _workbook('Missing PT Work State', headers)
    for pt in _pt_qs(run):
        snap = pt.calculation_snapshot or {}
        if not snap.get('missing_work_state') and pt.exemption_reason not in {
            'missing_work_state',
            'missing_pt_profile',
            'profile_missing_state',
        }:
            continue
        emp = pt.payroll_result.employee
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            pt.state_code or '',
            pt.tax_amount,
            pt.exemption_reason or 'Missing PT work-state / jurisdiction',
        ])
    return workbook_response(wb, f'pt_missing_work_state_run_{run.pk}.xlsx')


PT_REPORT_EXPORTS = {
    'pt_register': export_pt_register,
    'pt_monthly_summary': export_pt_monthly_summary,
    'missing_work_state': export_missing_pt_work_state,
}
