"""Form 16 preparation data — separate from the TDS calculation engine (Sprint 9.4).

Builds a structured payload / Excel preview from immutable payroll TDS
snapshots and employee tax masters. Does **not** recalculate tax.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollTDSResult, PreviousEmployerIncome, TaxDeclaration
from apps.compliance.services.tds_rules import financial_year_for_date, fy_date_bounds
from apps.payroll.models import PayrollRun, PayrollRunStatus


def _assert_exportable(run: PayrollRun) -> None:
    allowed = {
        PayrollRunStatus.CALCULATED,
        PayrollRunStatus.REVIEWED,
        PayrollRunStatus.APPROVED,
        PayrollRunStatus.LOCKED,
    }
    if run.status not in allowed:
        raise ValidationError(
            f'Payroll run must be Calculated/Reviewed/Approved/Locked for Form 16 data '
            f'(current: {run.status}).'
        )


def build_form16_employee_payload(run: PayrollRun, employee) -> dict[str, Any]:
    """Assemble Form 16 preparation fields for one employee from snapshots."""
    _assert_exportable(run)
    result = (
        run.results
        .filter(employee=employee)
        .select_related('tds_result', 'tds_result__rule_set')
        .first()
    )
    if result is None:
        raise ValidationError('No payroll result for this employee in the selected run.')

    try:
        tds = result.tds_result
    except PayrollTDSResult.DoesNotExist as exc:
        raise ValidationError('No TDS snapshot for this employee in the selected run.') from exc

    fy = tds.financial_year or financial_year_for_date(run.period.end_date)
    fy_start, fy_end = fy_date_bounds(fy)

    # FY-to-date TDS from snapshots (including this run).
    ytd_rows = (
        PayrollTDSResult.objects
        .filter(
            payroll_result__employee=employee,
            financial_year=fy,
            payroll_result__run__period__end_date__gte=fy_start,
            payroll_result__run__period__end_date__lte=run.period.end_date,
            payroll_result__run__status__in=[
                PayrollRunStatus.CALCULATED,
                PayrollRunStatus.REVIEWED,
                PayrollRunStatus.APPROVED,
                PayrollRunStatus.LOCKED,
            ],
        )
        .select_related('payroll_result__run__period')
        .order_by('payroll_result__run__period__end_date')
    )
    ytd_tds = sum((Decimal(r.monthly_tds) for r in ytd_rows), Decimal('0.00'))

    prev = PreviousEmployerIncome.objects.filter(employee=employee, financial_year=fy)
    prev_income = sum((Decimal(p.taxable_income) for p in prev), Decimal('0.00'))
    prev_tds = sum((Decimal(p.tds_deducted) for p in prev), Decimal('0.00'))

    decl = TaxDeclaration.objects.filter(employee=employee, financial_year=fy).first()
    pan = ''
    try:
        pan = employee.tax_profile.pan_number or ''
    except Exception:  # noqa: BLE001
        pan = ''

    snap = tds.calculation_snapshot or {}
    return {
        'employee_id': employee.pk,
        'employee_code': employee.employee_code,
        'employee_name': getattr(employee, 'full_name', str(employee)),
        'pan': pan,
        'financial_year': fy,
        'fy_start': fy_start.isoformat(),
        'fy_end': fy_end.isoformat(),
        'tax_regime': tds.tax_regime,
        'rule_code': tds.rule_set.code if tds.rule_set_id else '',
        'taxable_salary': str(tds.taxable_salary),
        'annual_tax': str(tds.annual_tax),
        'monthly_tds_this_run': str(tds.monthly_tds),
        'ytd_tds_deducted': str(ytd_tds),
        'cess': str(tds.cess),
        'rebate': str(tds.rebate),
        'surcharge': str(tds.surcharge),
        'relief': str(tds.relief),
        'previous_employer_income': str(prev_income),
        'previous_employer_tds': str(prev_tds),
        'declaration_status': decl.status if decl else '',
        'declaration_regime': decl.regime if decl else '',
        'projection': snap.get('projection', {}),
        'note': (
            'Form 16 preparation data only — assembled from PayrollTDSResult '
            'snapshots; tax is not recalculated here.'
        ),
    }


def build_form16_run_payload(run: PayrollRun) -> list[dict[str, Any]]:
    """Form 16 prep rows for every employee with a TDS snapshot on the run."""
    _assert_exportable(run)
    rows = []
    qs = (
        PayrollTDSResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result__employee')
        .order_by('payroll_result__employee__employee_code')
    )
    for tds in qs:
        rows.append(build_form16_employee_payload(run, tds.payroll_result.employee))
    return rows


def form16_excel_response(run: PayrollRun, employee=None) -> HttpResponse:
    """Excel export of Form 16 preparation data for a run (or one employee)."""
    if employee is not None:
        payloads = [build_form16_employee_payload(run, employee)]
        filename = f'form16_prep_run_{run.pk}_{employee.employee_code}.xlsx'
    else:
        payloads = build_form16_run_payload(run)
        filename = f'form16_prep_run_{run.pk}.xlsx'

    wb = Workbook()
    ws = wb.active
    ws.title = 'Form16 Prep'
    headers = [
        'Emp Code', 'Name', 'PAN', 'FY', 'Regime', 'Rule',
        'Taxable Salary', 'Annual Tax', 'Monthly TDS', 'YTD TDS',
        'Cess', 'Rebate', 'Surcharge', 'Prev Employer Income', 'Prev Employer TDS',
        'Declaration Status',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for p in payloads:
        ws.append([
            p['employee_code'],
            p['employee_name'],
            p['pan'],
            p['financial_year'],
            p['tax_regime'],
            p['rule_code'],
            p['taxable_salary'],
            p['annual_tax'],
            p['monthly_tds_this_run'],
            p['ytd_tds_deducted'],
            p['cess'],
            p['rebate'],
            p['surcharge'],
            p['previous_employer_income'],
            p['previous_employer_tds'],
            p['declaration_status'],
        ])
    stream = BytesIO()
    wb.save(stream)
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
