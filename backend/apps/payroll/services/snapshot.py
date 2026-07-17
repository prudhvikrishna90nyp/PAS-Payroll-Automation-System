"""Persist payroll result snapshots (Sprint 8.2 / 9.1 / 9.2)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction


@transaction.atomic
def snapshot_employee_result(run, calc_result):
    """Persist ``PayrollResult`` + components + PF/ESI results for one employee.

    Replaces any existing result row for the same run/employee.
    """
    from apps.compliance.models import PayrollESIResult, PayrollPFResult
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

    pf_calc = getattr(calc_result, 'pf_calculation', None)
    if pf_calc is not None:
        PayrollPFResult.objects.create(
            payroll_result=result,
            rule_set=pf_calc.rule_set,
            rule_version=pf_calc.rule_version or '',
            pf_wages=pf_calc.pf_wages,
            actual_pf_wages=pf_calc.actual_pf_wages,
            employee_pf=pf_calc.employee_pf,
            voluntary_pf=pf_calc.voluntary_pf,
            employer_pf=pf_calc.employer_pf,
            eps=pf_calc.eps,
            epf=pf_calc.epf,
            edli=pf_calc.edli,
            admin_charge=pf_calc.admin_charge,
            inspection_charge=pf_calc.inspection_charge,
            ncp_days=pf_calc.ncp_days,
            calculation_detail=pf_calc.to_detail_dict(),
        )

    esi_calc = getattr(calc_result, 'esi_calculation', None)
    if esi_calc is not None:
        PayrollESIResult.objects.create(
            payroll_result=result,
            rule_set=esi_calc.rule_set,
            rule_version=esi_calc.rule_version or '',
            esi_wages=esi_calc.esi_wages,
            employee_esi=esi_calc.employee_esi,
            employer_esi=esi_calc.employer_esi,
            is_eligible=esi_calc.eligible,
            above_wage_limit=esi_calc.above_wage_limit,
            continuity_applied=esi_calc.continuity_applied,
            daily_wage_exemption=esi_calc.daily_wage_exemption,
            missing_ip_number=esi_calc.missing_ip_number,
            eligibility_notes=esi_calc.eligibility_notes or '',
            calculation_detail=esi_calc.to_detail_dict(),
        )
    return result


def clear_run_results(run) -> int:
    """Delete all results (and cascaded components / PF / ESI results) for a run. Returns count."""
    from apps.payroll.models import PayrollResult
    from apps.payroll.services.locking import assert_run_unlocked_for_mutation

    assert_run_unlocked_for_mutation(run)
    deleted, _ = PayrollResult.objects.filter(run=run).delete()
    return deleted
