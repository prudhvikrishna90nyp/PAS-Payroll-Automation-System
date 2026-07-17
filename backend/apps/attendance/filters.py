from django.db.models import Q

from .models import Attendance, AttendancePeriod, Holiday, Shift


def filter_attendance(queryset, params):
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    employee = (params.get('employee') or '').strip()
    status = (params.get('status') or '').strip()
    date_from = (params.get('date_from') or '').strip()
    date_to = (params.get('date_to') or '').strip()
    period = (params.get('period') or '').strip()
    client = (params.get('client') or '').strip()

    if q:
        queryset = queryset.filter(
            Q(employee__employee_code__icontains=q)
            | Q(employee__first_name__icontains=q)
            | Q(employee__last_name__icontains=q)
            | Q(remarks__icontains=q)
        )
    if company:
        queryset = queryset.filter(employee__company_id=company)
    if client:
        queryset = queryset.filter(employee__company__client_id=client)
    if employee:
        queryset = queryset.filter(employee_id=employee)
    if status:
        queryset = queryset.filter(status=status)
    if date_from:
        queryset = queryset.filter(attendance_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(attendance_date__lte=date_to)
    if period:
        try:
            period_obj = AttendancePeriod.objects.get(pk=period)
            queryset = queryset.filter(
                employee__company_id=period_obj.company_id,
                attendance_date__gte=period_obj.start_date,
                attendance_date__lte=period_obj.end_date,
            )
        except (AttendancePeriod.DoesNotExist, ValueError, TypeError):
            pass
    return queryset


def attendance_list_queryset(params):
    qs = Attendance.objects.select_related(
        'employee',
        'employee__company',
        'employee__company__client',
        'shift',
    )
    return filter_attendance(qs, params)


def filter_shifts(queryset, params):
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    status = (params.get('status') or '').strip()
    if q:
        queryset = queryset.filter(
            Q(shift_code__icontains=q) | Q(shift_name__icontains=q)
        )
    if company:
        queryset = queryset.filter(company_id=company)
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)
    return queryset


def shift_list_queryset(params):
    return filter_shifts(
        Shift.objects.select_related('company', 'company__client'),
        params,
    )


def filter_holidays(queryset, params):
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    year = (params.get('year') or '').strip()
    holiday_type = (params.get('holiday_type') or '').strip()
    if q:
        queryset = queryset.filter(holiday_name__icontains=q)
    if company:
        queryset = queryset.filter(company_id=company)
    if year:
        queryset = queryset.filter(holiday_date__year=year)
    if holiday_type:
        queryset = queryset.filter(holiday_type=holiday_type)
    return queryset


def holiday_list_queryset(params):
    return filter_holidays(
        Holiday.objects.select_related('company', 'company__client'),
        params,
    )


def filter_periods(queryset, params):
    company = (params.get('company') or '').strip()
    year = (params.get('year') or '').strip()
    status = (params.get('status') or '').strip()
    if company:
        queryset = queryset.filter(company_id=company)
    if year:
        queryset = queryset.filter(year=year)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def period_list_queryset(params):
    return filter_periods(
        AttendancePeriod.objects.select_related('company', 'company__client'),
        params,
    )
