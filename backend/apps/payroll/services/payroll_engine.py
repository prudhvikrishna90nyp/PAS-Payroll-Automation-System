"""Payroll engine orchestration (periods, runs, calculation — Sprint 8.2)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from apps.payroll.models import (
    PayrollPeriod,
    PayrollPeriodStatus,
    PayrollRun,
    PayrollRunStatus,
)
from apps.payroll.services.audit import write_audit_log
from apps.payroll.services.attendance_loader import load_attendance_for_run
from apps.payroll.services.calculator import (
    eligible_employees_for_run,
    safe_calculate_employee,
)
from apps.payroll.services.exceptions import (
    EmployeeCalculationError,
    LockedRunError,
    MissingSalaryAssignmentError,
    RunNotCalculableError,
)
from apps.payroll.services.salary_loader import resolve_assignment_for_period
from apps.payroll.services.snapshot import clear_run_results, snapshot_employee_result
from apps.payroll.services.validation import (
    raise_if_errors,
    validate_payroll_period,
    validate_run_calculable,
    validate_run_creation,
)


@transaction.atomic
def create_period(
    *,
    company,
    month: int,
    year: int,
    start_date,
    end_date,
    user=None,
) -> PayrollPeriod:
    """Create an Open payroll period with uniqueness / overlap checks."""
    period = PayrollPeriod(
        company=company,
        month=month,
        year=year,
        start_date=start_date,
        end_date=end_date,
        status=PayrollPeriodStatus.OPEN,
        created_by=user,
        updated_by=user,
    )
    errors = validate_payroll_period(period)
    raise_if_errors(errors)
    period.save()
    write_audit_log(
        action='period_create',
        user=user,
        period=period,
        details={
            'month': month,
            'year': year,
            'status': period.status,
            'start_date': str(start_date),
            'end_date': str(end_date),
        },
    )
    return period


@transaction.atomic
def open_period(period: PayrollPeriod, user=None) -> PayrollPeriod:
    """Mark a payroll period Open (re-open if previously closed)."""
    previous = period.status
    period.status = PayrollPeriodStatus.OPEN
    update_fields = ['status', 'updated_at']
    if user is not None:
        period.updated_by = user
        update_fields.append('updated_by')
    period.save(update_fields=update_fields)
    write_audit_log(
        action='period_open',
        user=user,
        period=period,
        details={'previous_status': previous, 'status': period.status},
    )
    return period


@transaction.atomic
def close_period(period: PayrollPeriod, user=None) -> PayrollPeriod:
    """Mark a payroll period Closed."""
    if period.status == PayrollPeriodStatus.CLOSED:
        raise ValidationError('Payroll period is already closed.')
    previous = period.status
    period.status = PayrollPeriodStatus.CLOSED
    update_fields = ['status', 'updated_at']
    if user is not None:
        period.updated_by = user
        update_fields.append('updated_by')
    period.save(update_fields=update_fields)
    write_audit_log(
        action='period_close',
        user=user,
        period=period,
        details={'previous_status': previous, 'status': period.status},
    )
    return period


@transaction.atomic
def create_run(
    *,
    period: PayrollPeriod,
    user=None,
    notes: str = '',
    company=None,
) -> PayrollRun:
    """Create a Draft payroll run for an open company period."""
    company = company or period.company
    errors = validate_run_creation(period, company=company)
    raise_if_errors(errors)

    next_number = (
        PayrollRun.objects.filter(period=period).aggregate(m=Max('run_number')).get('m') or 0
    ) + 1

    run = PayrollRun(
        period=period,
        company=company,
        run_number=next_number,
        status=PayrollRunStatus.DRAFT,
        notes=notes or '',
        created_by=user,
    )
    run.full_clean()
    run.save()
    write_audit_log(
        action='run_create',
        user=user,
        period=period,
        run=run,
        details={
            'run_number': run.run_number,
            'status': run.status,
            'company_id': company.pk,
        },
    )
    return run


def _assert_run_calculable(run: PayrollRun) -> None:
    errors = validate_run_calculable(run)
    if not errors:
        return
    message = errors[0]
    if run.is_locked or run.status == PayrollRunStatus.LOCKED:
        raise LockedRunError(message)
    raise RunNotCalculableError(message)


@transaction.atomic
def calculate_run(run: PayrollRun, user=None) -> PayrollRun:
    """Run the full calculation pipeline for a payroll run.

    Pipeline:
      eligible employees → attendance loader → salary assignment loader →
      formula evaluation → proration → PayrollResult / component snapshot.

    Unlocked Draft / Calculated / Incomplete runs may be recalculated; previous
    results are replaced atomically. Locked (and reviewed/approved) runs are
    rejected. Per-employee failures do not create zero-salary results; errors
    are stored on the run and the status becomes Incomplete when any fail.
    Unexpected errors outside per-employee handling roll back the transaction.
    """
    run = PayrollRun.objects.select_for_update().select_related('period', 'company').get(pk=run.pk)
    _assert_run_calculable(run)

    previous_status = run.status
    employees = list(eligible_employees_for_run(run))
    attendance_map = load_attendance_for_run(run, employees=employees)

    # Replace prior snapshots for unlocked recalculation.
    clear_run_results(run)

    errors: list[dict] = []
    success_count = 0

    for employee in employees:
        sid = transaction.savepoint()
        try:
            try:
                assignment = resolve_assignment_for_period(employee, run.period)
            except MissingSalaryAssignmentError as exc:
                raise EmployeeCalculationError(
                    str(exc),
                    employee=employee,
                    code='missing_salary_assignment',
                ) from exc

            calc = safe_calculate_employee(
                employee=employee,
                period=run.period,
                assignment=assignment,
                attendance=attendance_map.get(employee.pk),
            )
            snapshot_employee_result(run, calc)
            transaction.savepoint_commit(sid)
            success_count += 1
        except EmployeeCalculationError as exc:
            transaction.savepoint_rollback(sid)
            entry = {
                'employee_id': employee.pk,
                'employee_code': employee.employee_code,
                'error': exc.message,
                'code': getattr(exc, 'code', 'employee_error'),
            }
            errors.append(entry)
            write_audit_log(
                action='employee_calculation_error',
                user=user,
                period=run.period,
                run=run,
                details=entry,
            )

    if errors:
        run.status = PayrollRunStatus.INCOMPLETE
    else:
        run.status = PayrollRunStatus.CALCULATED
    run.calculation_errors = errors
    run.save(update_fields=['status', 'calculation_errors', 'updated_at'])

    write_audit_log(
        action='run_calculate',
        user=user,
        period=run.period,
        run=run,
        details={
            'previous_status': previous_status,
            'status': run.status,
            'employee_count': len(employees),
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors,
        },
    )
    return run


@transaction.atomic
def process_company_run(run: PayrollRun, user=None) -> PayrollRun:
    """Alias for ``calculate_run`` (company-level processing entry point)."""
    return calculate_run(run, user=user)
