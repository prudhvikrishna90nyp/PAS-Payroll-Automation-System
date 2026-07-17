from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import (
    Attendance,
    AttendanceMonthlySummary,
    AttendancePeriod,
    AttendanceStatus,
    PeriodStatus,
    ShiftAssignment,
)


def period_for_date(company, attendance_date):
    return AttendancePeriod.objects.filter(
        company=company,
        start_date__lte=attendance_date,
        end_date__gte=attendance_date,
    ).first()


def assert_period_editable(company, attendance_date, user=None, *, allow_reopen_override=False):
    """Raise ValidationError/PermissionDenied when the period is not open for edits."""
    period = period_for_date(company, attendance_date)
    if period is None:
        return None
    if period.status == PeriodStatus.OPEN:
        return period
    if allow_reopen_override and user is not None and user.has_perm('attendance.reopen_attendanceperiod'):
        return period
    raise ValidationError(
        f'Attendance period {period.month:02d}/{period.year} is {period.get_status_display()} '
        'and cannot be edited.'
    )


def transition_period(period, new_status, user):
    """Apply open/lock/reopen/processed transitions with permission checks."""
    current = period.status
    new_status = str(new_status)

    allowed = {
        (PeriodStatus.OPEN, PeriodStatus.LOCKED),
        (PeriodStatus.LOCKED, PeriodStatus.OPEN),
        (PeriodStatus.LOCKED, PeriodStatus.PROCESSED),
        (PeriodStatus.PROCESSED, PeriodStatus.LOCKED),
    }
    if (current, new_status) not in allowed and current != new_status:
        raise ValidationError(
            f'Cannot change period status from {period.get_status_display()} to '
            f'{dict(PeriodStatus.choices).get(new_status, new_status)}.'
        )

    if new_status == PeriodStatus.OPEN and current == PeriodStatus.LOCKED:
        if not user.has_perm('attendance.reopen_attendanceperiod'):
            raise PermissionDenied('You do not have permission to reopen a locked period.')

    period.status = new_status
    period.updated_by = user
    period.save(update_fields=['status', 'updated_by', 'updated_at'])
    if new_status == PeriodStatus.LOCKED:
        generate_monthly_summaries(period, user=user)
    return period


def create_period_for_month(company, month, year, user=None):
    last_day = monthrange(year, month)[1]
    period = AttendancePeriod(
        company=company,
        month=month,
        year=year,
        start_date=date(year, month, 1),
        end_date=date(year, month, last_day),
        status=PeriodStatus.OPEN,
        created_by=user,
        updated_by=user,
    )
    period.full_clean()
    period.save()
    return period


def _time_to_minutes(value):
    return value.hour * 60 + value.minute


def calculate_attendance_metrics(attendance):
    """Compute worked/OT/late/early minutes from check-in/out and shift."""
    worked = Decimal('0.00')
    overtime = attendance.overtime_hours or Decimal('0.00')
    late = 0
    early = 0

    if attendance.check_in and attendance.check_out:
        start = datetime.combine(attendance.attendance_date, attendance.check_in)
        end = datetime.combine(attendance.attendance_date, attendance.check_out)
        if attendance.shift and attendance.shift.is_night_shift and end <= start:
            end += timedelta(days=1)
        elif end <= start:
            end += timedelta(days=1)
        delta_minutes = max(int((end - start).total_seconds() // 60), 0)
        if attendance.shift:
            delta_minutes = max(delta_minutes - int(attendance.shift.break_minutes or 0), 0)
        worked = (Decimal(delta_minutes) / Decimal('60')).quantize(Decimal('0.01'))

        if attendance.shift:
            full_day = attendance.shift.full_day_hours or Decimal('8.00')
            if worked > full_day and (attendance.overtime_hours or 0) == 0:
                overtime = (worked - full_day).quantize(Decimal('0.01'))
            grace_in = attendance.shift.grace_in_minutes or 0
            grace_out = attendance.shift.grace_out_minutes or 0
            in_diff = _time_to_minutes(attendance.check_in) - _time_to_minutes(attendance.shift.in_time)
            if in_diff > grace_in:
                late = in_diff - grace_in
            out_diff = _time_to_minutes(attendance.shift.out_time) - _time_to_minutes(attendance.check_out)
            if out_diff > grace_out and not attendance.shift.is_night_shift:
                early = out_diff - grace_out

    attendance.worked_hours = worked
    attendance.overtime_hours = overtime
    attendance.late_minutes = late
    attendance.early_exit_minutes = early
    return attendance


def resolve_shift_for_employee(employee, attendance_date):
    assignment = (
        ShiftAssignment.objects.filter(
            employee=employee,
            effective_from__lte=attendance_date,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=attendance_date))
        .select_related('shift')
        .order_by('-effective_from')
        .first()
    )
    return assignment.shift if assignment else None


def generate_monthly_summaries(period, user=None, employees=None):
    """Build/update AttendanceMonthlySummary rows for a period (payroll feed)."""
    from apps.employee.models import Employee

    qs = Employee.objects.filter(company=period.company, is_active=True)
    if employees is not None:
        qs = qs.filter(pk__in=[e.pk for e in employees])

    summaries = []
    for employee in qs:
        days = Attendance.objects.filter(
            employee=employee,
            attendance_date__gte=period.start_date,
            attendance_date__lte=period.end_date,
        )
        present = days.filter(status=AttendanceStatus.PRESENT).count()
        half = days.filter(status=AttendanceStatus.HALF_DAY).count()
        absent = days.filter(status=AttendanceStatus.ABSENT).count()
        paid_leave = days.filter(
            status__in=[
                AttendanceStatus.CASUAL_LEAVE,
                AttendanceStatus.SICK_LEAVE,
                AttendanceStatus.EARNED_LEAVE,
                AttendanceStatus.ON_DUTY,
            ]
        ).count()
        weekly_off = days.filter(status=AttendanceStatus.WEEKLY_OFF).count()
        holidays = days.filter(status=AttendanceStatus.HOLIDAY).count()
        lop = days.filter(status=AttendanceStatus.LOP).count()
        aggregates = days.aggregate(
            ot=Sum('overtime_hours'),
            late_rows=Count('id', filter=Q(late_minutes__gt=0)),
        )
        summary, _ = AttendanceMonthlySummary.objects.update_or_create(
            employee=employee,
            period=period,
            defaults={
                'present_days': Decimal(present) + (Decimal(half) * Decimal('0.50')),
                'absent_days': Decimal(absent),
                'paid_leave_days': Decimal(paid_leave),
                'weekly_off_days': Decimal(weekly_off),
                'holiday_days': Decimal(holidays),
                'half_days': Decimal(half),
                'overtime_hours': aggregates['ot'] or Decimal('0.00'),
                'late_count': aggregates['late_rows'] or 0,
                'lop_days': Decimal(lop),
                'updated_by': user,
                'created_by': user,
                'is_active': True,
            },
        )
        summaries.append(summary)
    return summaries


def touch_updated_by(instance, user):
    if user is not None and hasattr(instance, 'updated_by'):
        instance.updated_by = user
    if hasattr(instance, 'updated_at'):
        instance.updated_at = timezone.now()
