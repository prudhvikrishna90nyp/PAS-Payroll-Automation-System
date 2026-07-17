"""PF register and summary Excel reports (Sprint 9.1)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import EmployeePFProfile, PayrollPFResult
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


def _pf_qs(run: PayrollRun):
    return (
        PayrollPFResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )


def export_pf_register(run: PayrollRun) -> HttpResponse:
    headers = [
        'Emp Code', 'Name', 'UAN', 'Rule', 'Actual PF Wages', 'PF Wages',
        'EE PF', 'VPF', 'ER PF', 'EPS', 'ER EPF', 'EDLI', 'Admin', 'Inspection', 'NCP Days',
    ]
    wb, ws = _workbook('PF Register', headers)
    for pf in _pf_qs(run):
        emp = pf.payroll_result.employee
        profile = getattr(emp, 'pf_profile', None)
        uan = (profile.uan if profile else '') or getattr(emp, 'uan', '')
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            uan,
            pf.rule_version,
            pf.actual_pf_wages,
            pf.pf_wages,
            pf.employee_pf,
            pf.voluntary_pf,
            pf.employer_pf,
            pf.eps,
            pf.epf,
            pf.edli,
            pf.admin_charge,
            pf.inspection_charge,
            pf.ncp_days,
        ])
    return workbook_response(wb, f'pf_register_run_{run.pk}.xlsx')


def export_employee_contribution_register(run: PayrollRun) -> HttpResponse:
    headers = ['Emp Code', 'Name', 'UAN', 'PF Wages', 'EE PF', 'VPF', 'Total EE']
    wb, ws = _workbook('EE Contributions', headers)
    for pf in _pf_qs(run):
        emp = pf.payroll_result.employee
        profile = getattr(emp, 'pf_profile', None)
        uan = (profile.uan if profile else '') or getattr(emp, 'uan', '')
        total = Decimal(pf.employee_pf) + Decimal(pf.voluntary_pf)
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            uan,
            pf.pf_wages,
            pf.employee_pf,
            pf.voluntary_pf,
            total,
        ])
    return workbook_response(wb, f'pf_ee_register_run_{run.pk}.xlsx')


def export_employer_contribution_register(run: PayrollRun) -> HttpResponse:
    headers = [
        'Emp Code', 'Name', 'PF Wages', 'ER Total', 'EPS', 'ER EPF',
        'EDLI', 'Admin', 'Inspection',
    ]
    wb, ws = _workbook('ER Contributions', headers)
    for pf in _pf_qs(run):
        emp = pf.payroll_result.employee
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            pf.pf_wages,
            pf.employer_pf,
            pf.eps,
            pf.epf,
            pf.edli,
            pf.admin_charge,
            pf.inspection_charge,
        ])
    return workbook_response(wb, f'pf_er_register_run_{run.pk}.xlsx')


def export_monthly_pf_summary(run: PayrollRun) -> HttpResponse:
    headers = [
        'Metric', 'Amount',
    ]
    wb, ws = _workbook('Monthly PF Summary', headers)
    qs = _pf_qs(run)
    totals = {
        'Employees': qs.count(),
        'PF Wages': sum((p.pf_wages for p in qs), Decimal('0.00')),
        'EE PF': sum((p.employee_pf for p in qs), Decimal('0.00')),
        'VPF': sum((p.voluntary_pf for p in qs), Decimal('0.00')),
        'ER PF': sum((p.employer_pf for p in qs), Decimal('0.00')),
        'EPS': sum((p.eps for p in qs), Decimal('0.00')),
        'ER EPF': sum((p.epf for p in qs), Decimal('0.00')),
        'EDLI': sum((p.edli for p in qs), Decimal('0.00')),
        'Admin': sum((p.admin_charge for p in qs), Decimal('0.00')),
    }
    for key, value in totals.items():
        ws.append([key, value])
    return workbook_response(wb, f'pf_monthly_summary_run_{run.pk}.xlsx')


def export_missing_uan(run: PayrollRun) -> HttpResponse:
    headers = ['Emp Code', 'Name', 'PF Applicable', 'UAN']
    wb, ws = _workbook('Missing UAN', headers)
    for pf in _pf_qs(run):
        emp = pf.payroll_result.employee
        profile = getattr(emp, 'pf_profile', None)
        uan = (profile.uan if profile else '') or getattr(emp, 'uan', '')
        if uan:
            continue
        applicable = True
        if profile is not None:
            applicable = profile.is_pf_applicable
        else:
            applicable = getattr(emp, 'pf_eligible', True)
        if not applicable:
            continue
        ws.append([emp.employee_code, getattr(emp, 'full_name', str(emp)), 'Yes', ''])
    return workbook_response(wb, f'pf_missing_uan_run_{run.pk}.xlsx')


def export_higher_pension(run: PayrollRun) -> HttpResponse:
    headers = ['Emp Code', 'Name', 'UAN', 'Actual PF Wages', 'PF Wages', 'EPS']
    wb, ws = _workbook('Higher Pension', headers)
    for pf in _pf_qs(run):
        detail = pf.calculation_detail or {}
        if not detail.get('higher_pension'):
            continue
        emp = pf.payroll_result.employee
        profile = getattr(emp, 'pf_profile', None)
        uan = (profile.uan if profile else '') or getattr(emp, 'uan', '')
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            uan,
            pf.actual_pf_wages,
            pf.pf_wages,
            pf.eps,
        ])
    return workbook_response(wb, f'pf_higher_pension_run_{run.pk}.xlsx')


REPORT_EXPORTS = {
    'pf_register': export_pf_register,
    'ee_contribution': export_employee_contribution_register,
    'er_contribution': export_employer_contribution_register,
    'monthly_summary': export_monthly_pf_summary,
    'missing_uan': export_missing_uan,
    'higher_pension': export_higher_pension,
}
