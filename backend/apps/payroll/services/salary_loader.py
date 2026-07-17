"""Load effective salary assignments for a payroll run (Sprint 8.2).

Resolution rule: the assignment whose effective-date range covers the
payroll period ``end_date`` (and is not soft-deleted). If none covers
``end_date``, fall back to any assignment overlapping the period window.
"""

from __future__ import annotations

from django.db.models import Q

from apps.payroll.services.exceptions import MissingSalaryAssignmentError


def resolve_assignment_for_period(employee, period):
    """Return the ``EmployeeSalaryAssignment`` effective for ``period``.

    Raises ``MissingSalaryAssignmentError`` when none is found.
    """
    from apps.payroll.models import EmployeeSalaryAssignment

    end = period.end_date
    start = period.start_date

    qs = (
        EmployeeSalaryAssignment.objects
        .filter(employee_id=employee.pk, is_deleted=False, is_active=True)
        .select_related('salary_structure')
        .order_by('-effective_from', '-id')
    )

    covering_end = qs.filter(
        effective_from__lte=end,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=end))
    assignment = covering_end.first()
    if assignment is not None:
        return assignment

    overlapping = qs.filter(effective_from__lte=end).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=start)
    )
    assignment = overlapping.first()
    if assignment is not None:
        return assignment

    raise MissingSalaryAssignmentError(
        f'No salary assignment covering {end} for {employee.employee_code}.',
        employee=employee,
    )


def load_salary_for_run(run, employees=None) -> dict:
    """Return ``employee_id → assignment`` for eligible employees.

    Missing assignments are omitted; the orchestrator records per-employee
    errors instead of inventing zero pay.
    """
    if employees is None:
        from apps.payroll.services.calculator import eligible_employees_for_run

        employees = list(eligible_employees_for_run(run))

    mapping: dict = {}
    for employee in employees:
        try:
            mapping[employee.pk] = resolve_assignment_for_period(employee, run.period)
        except MissingSalaryAssignmentError:
            continue
    return mapping
