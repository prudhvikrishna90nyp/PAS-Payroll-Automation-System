from django.shortcuts import render

from apps.attendance.models import AttendanceRecord
from apps.employee.models import Employee


def attendance_list(request):
    records = AttendanceRecord.objects.select_related('employee').order_by('-date')[:50]
    return render(
        request,
        'attendance/attendance_list.html',
        {
            'records': records,
            'employee_count': Employee.objects.filter(is_active=True).count(),
        },
    )
