"""ESI contribution export (separate from calculation — Sprint 9.2)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollESIResult
from apps.compliance.services.esi_engine import resolve_ip_number
from apps.payroll.models import PayrollRun, PayrollRunStatus


EXPORTABLE_STATUSES = {
    PayrollRunStatus.CALCULATED,
    PayrollRunStatus.REVIEWED,
    PayrollRunStatus.APPROVED,
    PayrollRunStatus.LOCKED,
}

CONTRIBUTION_HEADERS = [
    'IP Number',
    'Emp Code',
    'Name',
    'ESI Wages',
    'EE ESI',
    'ER ESI',
    'Total',
    'Rule',
    'Eligible',
    'Notes',
]


def _assert_exportable(run: PayrollRun) -> None:
    if run.status not in EXPORTABLE_STATUSES:
        raise ValidationError(
            f'Payroll run must be Calculated/Reviewed/Approved/Locked to export ESI '
            f'(current status: {run.get_status_display()}).'
        )


def iter_esi_contribution_rows(run: PayrollRun, *, require_ip: bool = False):
    """Yield contribution dicts from immutable ``PayrollESIResult`` snapshots."""
    _assert_exportable(run)
    qs = (
        PayrollESIResult.objects
        .filter(payroll_result__run=run, is_eligible=True)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )
    missing = []
    for row in qs:
        emp = row.payroll_result.employee
        ip = resolve_ip_number(emp)
        if not ip:
            missing.append(emp.employee_code)
            if require_ip:
                continue
        yield {
            'ip_number': ip,
            'employee_code': emp.employee_code,
            'name': getattr(emp, 'full_name', str(emp)),
            'esi_wages': row.esi_wages,
            'employee_esi': row.employee_esi,
            'employer_esi': row.employer_esi,
            'total': Decimal(row.employee_esi) + Decimal(row.employer_esi),
            'rule_version': row.rule_version,
            'eligible': row.is_eligible,
            'notes': row.eligibility_notes,
        }
    if require_ip and missing:
        raise ValidationError(
            'Missing ESI IP number for: ' + ', '.join(missing)
        )


def build_esi_contribution_workbook(run: PayrollRun, *, require_ip: bool = False) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = 'ESI Contribution'
    ws.append(CONTRIBUTION_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in iter_esi_contribution_rows(run, require_ip=require_ip):
        ws.append([
            row['ip_number'],
            row['employee_code'],
            row['name'],
            row['esi_wages'],
            row['employee_esi'],
            row['employer_esi'],
            row['total'],
            row['rule_version'],
            'Yes' if row['eligible'] else 'No',
            row['notes'],
        ])
    return wb


def esi_contribution_excel_response(run: PayrollRun, *, require_ip: bool = False) -> HttpResponse:
    wb = build_esi_contribution_workbook(run, require_ip=require_ip)
    stream = BytesIO()
    wb.save(stream)
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="esi_contribution_run_{run.pk}.xlsx"'
    return response
