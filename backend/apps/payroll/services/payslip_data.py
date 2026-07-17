"""Payslip presentation data sourced exclusively from payroll snapshots."""
from decimal import Decimal, ROUND_HALF_UP

from apps.employee.models import Employee
from apps.payroll.models import ComponentType, PayrollResult
from .report_queries import is_final_status, status_label_for_display

CENT = Decimal("0.01")


def _money(value):
    return (value if value is not None else Decimal("0.00")).quantize(CENT, rounding=ROUND_HALF_UP)


def _named(instance, attribute):
    return getattr(instance, attribute, "") if instance else ""


def build_payslip_dataset(result: PayrollResult) -> dict:
    """Build a printable dataset without recalculating or reading salary masters."""
    run = result.run
    period = run.period
    employee = Employee.all_objects.select_related("branch", "department", "designation").get(pk=result.employee_id)
    components = list(result.components.all())

    def lines(component_type):
        return [
            {"code": line.component_code, "name": line.component_name, "amount": _money(line.amount)}
            for line in sorted((item for item in components if item.component_type == component_type), key=lambda item: item.component_code)
        ]

    final = is_final_status(run.status)
    status = status_label_for_display(run.status)
    return {
        "company": {"id": run.company_id, "name": run.company.company_name},
        "employee": {
            "id": employee.pk, "code": employee.employee_code, "name": employee.full_name,
            "branch": _named(employee.branch, "branch_name"),
            "department": _named(employee.department, "name"),
            "designation": _named(employee.designation, "name"),
            "is_archived": bool(employee.is_deleted),
        },
        "period": {"id": period.pk, "month": period.month, "year": period.year, "start_date": period.start_date, "end_date": period.end_date},
        "run": {"id": run.pk, "run_number": run.run_number, "status": run.status, "status_label": status, "is_final": final, "is_draft_watermark": not final},
        "attendance": {"present_days": result.present_days, "absent_days": result.absent_days, "lop_days": result.lop_days, "overtime_hours": result.overtime_hours},
        "earnings": lines(ComponentType.EARNING),
        "deductions": lines(ComponentType.DEDUCTION),
        "employer_contributions": lines(ComponentType.EMPLOYER_CONTRIBUTION),
        "gross": _money(result.gross), "total_earnings": _money(result.total_earnings),
        "total_deductions": _money(result.total_deductions), "net": _money(result.net_salary),
        "ctc_snapshot": _money(result.ctc_snapshot),
        "payment_details": {"bank_name": employee.bank_name, "account_number": employee.bank_account_number, "ifsc": employee.ifsc_code, "account_holder": employee.account_holder_name},
        "watermark": None if final else "DRAFT",
        "status_banner": f"Final payroll ({status})" if final else "DRAFT — not final payroll",
        "calculation_reference": {"run_id": run.pk, "run_number": run.run_number, "result_id": result.pk, "period": f"{period.month:02d}/{period.year}"},
        "amounts_source": "payroll_result_snapshot",
    }


def build_payslip_dataset_for_run_employee(run, employee):
    result = PayrollResult.objects.filter(run=run, employee=employee).select_related("run", "run__company", "run__period").prefetch_related("components").first()
    return build_payslip_dataset(result) if result else None
