"""EPFO ECR export (Sprint 9.1).

ECR text columns (tab-separated), documented for EPFO upload tooling:

1. UAN
2. Member Name
3. Gross Wages
4. EPF Wages
5. EPS Wages
6. EDLI Wages
7. EE Share (EPF contribution)
8. EPS Contribution (ER)
9. ER EPF Difference (ER PF − EPS)
10. NCP Days
11. Refund of Advances (default 0)

Also available as Excel via ``build_ecr_workbook``.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.compliance.models import PayrollPFResult
from apps.compliance.services.validator import validate_uan_value
from apps.payroll.models import PayrollRun, PayrollRunStatus


ECR_HEADERS = [
    'UAN',
    'Member Name',
    'Gross Wages',
    'EPF Wages',
    'EPS Wages',
    'EDLI Wages',
    'EE Share',
    'EPS Contribution',
    'ER EPF Difference',
    'NCP Days',
    'Refund of Advances',
]

EXPORTABLE_STATUSES = {
    PayrollRunStatus.CALCULATED,
    PayrollRunStatus.REVIEWED,
    PayrollRunStatus.APPROVED,
    PayrollRunStatus.LOCKED,
}


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _member_name(employee) -> str:
    return (getattr(employee, 'full_name', None) or str(employee)).strip()


def _uan_for_result(pf_result: PayrollPFResult, employee) -> str:
    profile = getattr(employee, 'pf_profile', None)
    if profile is not None and profile.uan:
        return profile.uan
    return getattr(employee, 'uan', '') or ''


def iter_ecr_rows(run: PayrollRun, *, validate_uans: bool = True):
    """Yield ECR row dicts for employees with a PayrollPFResult on the run."""
    if run.status not in EXPORTABLE_STATUSES:
        raise ValidationError(
            'ECR export requires a calculated, reviewed, approved, or locked run.'
        )

    qs = (
        PayrollPFResult.objects
        .filter(payroll_result__run=run)
        .select_related('payroll_result', 'payroll_result__employee', 'rule_set')
        .order_by('payroll_result__employee__employee_code')
    )

    rows = []
    errors = []
    for pf in qs:
        result = pf.payroll_result
        employee = result.employee
        detail = pf.calculation_detail or {}
        if detail.get('eligible') is False and pf.pf_wages == 0 and pf.employee_pf == 0:
            continue

        uan = _uan_for_result(pf, employee)
        if validate_uans:
            if not uan:
                errors.append(f'{employee.employee_code}: missing UAN')
            else:
                try:
                    uan = validate_uan_value(uan)
                except ValidationError as exc:
                    errors.append(f'{employee.employee_code}: {exc.messages[0]}')

        eps_wages = pf.pf_wages
        if detail.get('higher_pension'):
            eps_wages = pf.actual_pf_wages

        rows.append({
            'uan': uan or '',
            'member_name': _member_name(employee),
            'gross_wages': _q(result.gross),
            'epf_wages': _q(pf.pf_wages),
            'eps_wages': _q(eps_wages),
            'edli_wages': _q(pf.pf_wages),
            'ee_share': _q(pf.employee_pf + pf.voluntary_pf),
            'eps_contribution': _q(pf.eps),
            'er_epf_difference': _q(pf.epf),
            'ncp_days': _q(pf.ncp_days),
            'refund': Decimal('0.00'),
            'employee_code': employee.employee_code,
        })

    if validate_uans and errors:
        raise ValidationError(errors)
    return rows


def build_ecr_text(run: PayrollRun, *, validate_uans: bool = True) -> str:
    """Tab-separated ECR body (no header — EPFO style)."""
    lines = []
    for row in iter_ecr_rows(run, validate_uans=validate_uans):
        lines.append('\t'.join([
            str(row['uan']),
            str(row['member_name']),
            f"{row['gross_wages']:.2f}",
            f"{row['epf_wages']:.2f}",
            f"{row['eps_wages']:.2f}",
            f"{row['edli_wages']:.2f}",
            f"{row['ee_share']:.2f}",
            f"{row['eps_contribution']:.2f}",
            f"{row['er_epf_difference']:.2f}",
            f"{row['ncp_days']:.0f}" if row['ncp_days'] == int(row['ncp_days']) else f"{row['ncp_days']:.2f}",
            f"{row['refund']:.2f}",
        ]))
    return '\n'.join(lines) + ('\n' if lines else '')


def build_ecr_workbook(run: PayrollRun, *, validate_uans: bool = True) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = 'ECR'
    ws.append(ECR_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in iter_ecr_rows(run, validate_uans=validate_uans):
        ws.append([
            row['uan'],
            row['member_name'],
            row['gross_wages'],
            row['epf_wages'],
            row['eps_wages'],
            row['edli_wages'],
            row['ee_share'],
            row['eps_contribution'],
            row['er_epf_difference'],
            row['ncp_days'],
            row['refund'],
        ])
    return wb


def ecr_text_response(run: PayrollRun, *, validate_uans: bool = True) -> HttpResponse:
    content = build_ecr_text(run, validate_uans=validate_uans)
    filename = f'ecr_run_{run.pk}.txt'
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def ecr_excel_response(run: PayrollRun, *, validate_uans: bool = True) -> HttpResponse:
    wb = build_ecr_workbook(run, validate_uans=validate_uans)
    stream = BytesIO()
    wb.save(stream)
    filename = f'ecr_run_{run.pk}.xlsx'
    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
