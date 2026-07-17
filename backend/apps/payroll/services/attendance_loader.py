"""Load attendance summaries for a payroll run (Sprint 8.2).

Maps ``PayrollPeriod`` (company/month/year) to ``AttendanceMonthlySummary``
when an ``AttendancePeriod`` exists for the same company calendar month.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AttendanceSnapshot:
    """Normalized attendance inputs for one employee in a payroll period."""

    present_days: Decimal = Decimal('0.00')
    absent_days: Decimal = Decimal('0.00')
    lop_days: Decimal = Decimal('0.00')
    overtime_hours: Decimal = Decimal('0.00')
    half_days: Decimal = Decimal('0.00')
    paid_leave_days: Decimal = Decimal('0.00')
    weekly_off_days: Decimal = Decimal('0.00')
    holiday_days: Decimal = Decimal('0.00')
    source: str = 'default'  # 'summary' | 'default'


def _d(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _snapshot_from_summary(summary) -> AttendanceSnapshot:
    return AttendanceSnapshot(
        present_days=_d(summary.present_days),
        absent_days=_d(summary.absent_days),
        lop_days=_d(summary.lop_days),
        overtime_hours=_d(summary.overtime_hours),
        half_days=_d(summary.half_days),
        paid_leave_days=_d(summary.paid_leave_days),
        weekly_off_days=_d(summary.weekly_off_days),
        holiday_days=_d(summary.holiday_days),
        source='summary',
    )


def load_attendance_for_employee(employee, period) -> AttendanceSnapshot:
    """Return attendance snapshot for one employee in a PayrollPeriod."""
    from apps.attendance.models import AttendanceMonthlySummary, AttendancePeriod

    att_period = (
        AttendancePeriod.objects
        .filter(company_id=period.company_id, month=period.month, year=period.year)
        .first()
    )
    if att_period is None:
        return AttendanceSnapshot()

    summary = (
        AttendanceMonthlySummary.objects
        .filter(employee_id=employee.pk, period=att_period)
        .first()
    )
    if summary is None:
        return AttendanceSnapshot()
    return _snapshot_from_summary(summary)


def load_attendance_for_run(run, employees=None) -> dict[int, AttendanceSnapshot]:
    """Return ``employee_id → AttendanceSnapshot`` for the run's period.

    Employees without a monthly summary receive a default zero snapshot; the
    calculator treats that as full eligible days minus LOP (0).
    """
    from apps.attendance.models import AttendanceMonthlySummary, AttendancePeriod

    if employees is None:
        from apps.payroll.services.calculator import eligible_employees_for_run

        employees = list(eligible_employees_for_run(run))

    period = run.period
    result: dict[int, AttendanceSnapshot] = {
        emp.pk: AttendanceSnapshot() for emp in employees
    }

    att_period = (
        AttendancePeriod.objects
        .filter(company_id=period.company_id, month=period.month, year=period.year)
        .first()
    )
    if att_period is None or not result:
        return result

    summaries = AttendanceMonthlySummary.objects.filter(
        period=att_period,
        employee_id__in=result.keys(),
    )
    for summary in summaries:
        result[summary.employee_id] = _snapshot_from_summary(summary)
    return result
