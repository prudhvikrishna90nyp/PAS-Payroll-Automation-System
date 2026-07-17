"""PT challan / return-preparation export (Sprint 9.3).

Exports reconcile from immutable ``PayrollPTResult`` snapshots only.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollPTResult
from apps.payroll.models import PayrollRun, PayrollRunStatus


CHALLAN_HEADERS = [
    'Emp Code',
    'Name',
    'State',
    'PT Wages',
    'Tax Amount',
    'Exemption Reason',
    'Special Month',
    'Rule',
]


def _assert_exportable(run: PayrollRun) -> None:
    allowed = {
        PayrollRunStatus.CALCULATED,
        PayrollRunStatus.REVIEWED,
        PayrollRunStatus.APPROVED,
        PayrollRunStatus.LOCKED,
    }
    if run.status not in allowed:
        raise ValidationError(
            f'Payroll run must be Calculated/Reviewed/Approved/Locked to export PT '
            f'challan data (current: {run.status}).'
        )


def iter_pt_challan_rows(run: PayrollRun):
    """Yield challan/return dicts from immutable ``PayrollPTResult`` snapshots."""
    _assert_exportable(run)
    qs = (
        PayrollPTResult.objects
        .filter(payroll_result__run=run)
        .select_related(
            'payroll_result',
            'payroll_result__employee',
            'rule_set',
        )
        .order_by('payroll_result__employee__employee_code')
    )
    for row in qs:
        emp = row.payroll_result.employee
        snap = row.calculation_snapshot or {}
        yield {
            'employee_code': emp.employee_code,
            'name': getattr(emp, 'full_name', str(emp)),
            'state_code': row.state_code,
            'pt_wages': row.pt_wages,
            'tax_amount': row.tax_amount,
            'exemption_reason': row.exemption_reason,
            'special_month': 'Yes' if snap.get('special_month_applied') else 'No',
            'rule': row.rule_set.name if row.rule_set_id else '',
        }


def build_pt_challan_workbook(run: PayrollRun) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = 'PT Challan'
    ws.append(CHALLAN_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    total = Decimal('0.00')
    for row in iter_pt_challan_rows(run):
        ws.append([
            row['employee_code'],
            row['name'],
            row['state_code'],
            row['pt_wages'],
            row['tax_amount'],
            row['exemption_reason'],
            row['special_month'],
            row['rule'],
        ])
        total += Decimal(row['tax_amount'])
    ws.append([])
    ws.append(['TOTAL TAX', '', '', '', total, '', '', ''])
    return wb


def pt_challan_excel_response(run: PayrollRun) -> HttpResponse:
    wb = build_pt_challan_workbook(run)
    stream = BytesIO()
    wb.save(stream)
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="pt_challan_run_{run.pk}.xlsx"'
    return response
