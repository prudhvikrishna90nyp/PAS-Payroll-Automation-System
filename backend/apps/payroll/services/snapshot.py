"""Persist payroll result snapshots (Sprint 8.2)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction


@transaction.atomic
def snapshot_employee_result(run, calc_result):
    """Persist ``PayrollResult`` + ``PayrollResultComponent`` for one employee.

    Replaces any existing result row for the same run/employee.
    """
    from apps.payroll.models import PayrollResult, PayrollResultComponent
    from apps.payroll.services.locking import assert_run_unlocked_for_mutation

    assert_run_unlocked_for_mutation(run)

    employee = calc_result.employee
    PayrollResult.objects.filter(run=run, employee=employee).delete()

    result = PayrollResult.objects.create(
        run=run,
        employee=employee,
        present_days=calc_result.present_days,
        absent_days=calc_result.absent_days,
        lop_days=calc_result.lop_days,
        overtime_hours=calc_result.overtime_hours,
        gross=calc_result.gross,
        total_earnings=calc_result.total_earnings,
        total_deductions=calc_result.total_deductions,
        net_salary=calc_result.net_salary,
        ctc_snapshot=calc_result.ctc_snapshot,
    )

    component_rows = []
    for row in calc_result.components:
        detail = dict(row.get('calculation_detail') or {})
        detail.update(calc_result.calculation_detail)
        component_rows.append(
            PayrollResultComponent(
                result=result,
                component_code=row['component_code'],
                component_name=row['component_name'],
                component_type=row['component_type'],
                amount=Decimal(row['amount']),
                calculation_detail=detail,
            )
        )
    if component_rows:
        PayrollResultComponent.objects.bulk_create(component_rows)
    return result


def clear_run_results(run) -> int:
    """Delete all results (and cascaded components) for a run. Returns count."""
    from apps.payroll.models import PayrollResult
    from apps.payroll.services.locking import assert_run_unlocked_for_mutation

    assert_run_unlocked_for_mutation(run)
    deleted, _ = PayrollResult.objects.filter(run=run).delete()
    return deleted
