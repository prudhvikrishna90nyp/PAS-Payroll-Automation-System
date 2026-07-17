"""TDS register Excel export (Sprint 9.4).

Exports reconcile from immutable ``PayrollTDSResult`` snapshots only.
"""

from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollTDSResult
from apps.payroll.models import PayrollRun, PayrollRunStatus


REGISTER_HEADERS = [
    'Emp Code',
    'Name',
    'PAN',
    'FY',
    'Regime',
    'Rule',
    'Taxable Income',
    'Annual Tax',
    'Monthly TDS',
    'Cess',
    'Rebate',
    'Surcharge',
    'Previous TDS',
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
            f'Payroll run must be Calculated/Reviewed/Approved/Locked to export TDS '
            f'data (current: {run.status}).'
        )


def iter_tds_register_rows(run: PayrollRun):
    """Yield TDS register dicts from immutable ``PayrollTDSResult`` snapshots."""
    _assert_exportable(run)
    qs = (
        PayrollTDSResult.objects
        .filter(payroll_result__run=run)
        .select_related(
            'payroll_result',
            'payroll_result__employee',
            'payroll_result__employee__tax_profile',
            'rule_set',
        )
        .order_by('payroll_result__employee__employee_code')
    )
    for row in qs:
        emp = row.payroll_result.employee
        pan = ''
        try:
            pan = emp.tax_profile.pan_number or ''
        except Exception:  # noqa: BLE001
            pan = ''
        yield {
            'employee_code': emp.employee_code,
            'name': getattr(emp, 'full_name', str(emp)),
            'pan': pan,
            'financial_year': row.financial_year,
            'tax_regime': row.tax_regime,
            'rule': row.rule_set.code if row.rule_set_id else '',
            'taxable_salary': row.taxable_salary,
            'annual_tax': row.annual_tax,
            'monthly_tds': row.monthly_tds,
            'cess': row.cess,
            'rebate': row.rebate,
            'surcharge': row.surcharge,
            'previous_tds': row.previous_tds,
        }


def build_tds_register_workbook(run: PayrollRun) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = 'TDS Register'
    ws.append(REGISTER_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in iter_tds_register_rows(run):
        ws.append([
            row['employee_code'],
            row['name'],
            row['pan'],
            row['financial_year'],
            row['tax_regime'],
            row['rule'],
            row['taxable_salary'],
            row['annual_tax'],
            row['monthly_tds'],
            row['cess'],
            row['rebate'],
            row['surcharge'],
            row['previous_tds'],
        ])
    return wb


def tds_register_excel_response(run: PayrollRun) -> HttpResponse:
    wb = build_tds_register_workbook(run)
    stream = BytesIO()
    wb.save(stream)
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="tds_register_run_{run.pk}.xlsx"'
    return response
