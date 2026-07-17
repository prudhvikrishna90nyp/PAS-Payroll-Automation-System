"""ESI register and summary Excel reports (Sprint 9.2).

Reports reconcile from immutable ``PayrollESIResult`` snapshots only.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollESIResult
from apps.compliance.services.esi_engine import resolve_ip_number
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


def _esi_qs(run: PayrollRun):
    return (
        PayrollESIResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )


def export_esi_register(run: PayrollRun) -> HttpResponse:
    headers = [
        'Emp Code', 'Name', 'IP Number', 'Rule', 'ESI Wages',
        'EE ESI', 'ER ESI', 'Eligible', 'Above Limit', 'Continuity',
        'Daily Exempt', 'Missing IP', 'Notes',
    ]
    wb, ws = _workbook('ESI Register', headers)
    for esi in _esi_qs(run):
        emp = esi.payroll_result.employee
        ip = resolve_ip_number(emp)
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            ip,
            esi.rule_version,
            esi.esi_wages,
            esi.employee_esi,
            esi.employer_esi,
            'Yes' if esi.is_eligible else 'No',
            'Yes' if esi.above_wage_limit else 'No',
            'Yes' if esi.continuity_applied else 'No',
            'Yes' if esi.daily_wage_exemption else 'No',
            'Yes' if esi.missing_ip_number else 'No',
            esi.eligibility_notes,
        ])
    return workbook_response(wb, f'esi_register_run_{run.pk}.xlsx')


def export_esi_monthly_summary(run: PayrollRun) -> HttpResponse:
    headers = ['Metric', 'Amount']
    wb, ws = _workbook('Monthly ESI Summary', headers)
    qs = list(_esi_qs(run))
    eligible = [e for e in qs if e.is_eligible]
    totals = {
        'Employees (all)': len(qs),
        'Employees (eligible)': len(eligible),
        'ESI Wages': sum((e.esi_wages for e in eligible), Decimal('0.00')),
        'EE ESI': sum((e.employee_esi for e in eligible), Decimal('0.00')),
        'ER ESI': sum((e.employer_esi for e in eligible), Decimal('0.00')),
        'Total Contribution': sum(
            (Decimal(e.employee_esi) + Decimal(e.employer_esi) for e in eligible),
            Decimal('0.00'),
        ),
        'Missing IP (eligible)': sum(1 for e in eligible if e.missing_ip_number),
        'Continuity applied': sum(1 for e in eligible if e.continuity_applied),
        'Daily wage exemption': sum(1 for e in eligible if e.daily_wage_exemption),
    }
    for key, value in totals.items():
        ws.append([key, value])
    return workbook_response(wb, f'esi_monthly_summary_run_{run.pk}.xlsx')


def export_missing_ip(run: PayrollRun) -> HttpResponse:
    """Report ESI-applicable / eligible employees missing an IP number (never silent)."""
    headers = ['Emp Code', 'Name', 'ESI Applicable', 'Eligible', 'IP Number', 'Notes']
    wb, ws = _workbook('Missing IP', headers)
    for esi in _esi_qs(run):
        if not esi.missing_ip_number and not (
            esi.is_eligible and not resolve_ip_number(esi.payroll_result.employee)
        ):
            # Include rows flagged missing OR eligible without IP
            if not esi.missing_ip_number:
                continue
        emp = esi.payroll_result.employee
        ip = resolve_ip_number(emp)
        if ip and not esi.missing_ip_number:
            continue
        if ip:
            continue
        profile = getattr(emp, 'esi_profile', None)
        applicable = True
        if profile is not None:
            applicable = profile.is_esi_applicable
        else:
            applicable = getattr(emp, 'esi_eligible', False)
        if not applicable and not esi.is_eligible:
            continue
        ws.append([
            emp.employee_code,
            getattr(emp, 'full_name', str(emp)),
            'Yes' if applicable else 'No',
            'Yes' if esi.is_eligible else 'No',
            '',
            esi.eligibility_notes or 'Missing ESI IP number',
        ])
    return workbook_response(wb, f'esi_missing_ip_run_{run.pk}.xlsx')


ESI_REPORT_EXPORTS = {
    'esi_register': export_esi_register,
    'esi_monthly_summary': export_esi_monthly_summary,
    'missing_ip': export_missing_ip,
}
