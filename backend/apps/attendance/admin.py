from django.contrib import admin

from .models import (
    Attendance,
    AttendanceMonthlySummary,
    AttendancePeriod,
    Holiday,
    Shift,
    ShiftAssignment,
    WeeklyOff,
)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        'shift_code',
        'shift_name',
        'company',
        'in_time',
        'out_time',
        'is_night_shift',
        'is_active',
    )
    list_filter = ('company', 'is_night_shift', 'is_active')
    search_fields = ('shift_code', 'shift_name', 'company__company_name')


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('holiday_date', 'holiday_name', 'holiday_type', 'company', 'is_active')
    list_filter = ('holiday_type', 'company', 'is_active')
    search_fields = ('holiday_name', 'company__company_name')
    date_hierarchy = 'holiday_date'


@admin.register(AttendancePeriod)
class AttendancePeriodAdmin(admin.ModelAdmin):
    list_display = ('company', 'month', 'year', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'year', 'company')
    search_fields = ('company__company_name',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'attendance_date',
        'status',
        'shift',
        'check_in',
        'check_out',
        'worked_hours',
        'overtime_hours',
        'approved',
    )
    list_filter = ('status', 'approved', 'attendance_date')
    search_fields = (
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
    )
    date_hierarchy = 'attendance_date'
    autocomplete_fields = ('employee', 'shift')


@admin.register(WeeklyOff)
class WeeklyOffAdmin(admin.ModelAdmin):
    list_display = ('employee', 'weekday', 'effective_from', 'effective_to', 'is_active')
    list_filter = ('weekday', 'is_active')
    search_fields = ('employee__employee_code',)


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'shift', 'effective_from', 'effective_to', 'is_active')
    list_filter = ('shift', 'is_active')
    search_fields = ('employee__employee_code', 'shift__shift_code')


@admin.register(AttendanceMonthlySummary)
class AttendanceMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'period',
        'present_days',
        'absent_days',
        'overtime_hours',
        'lop_days',
    )
    list_filter = ('period__year', 'period__month')
    search_fields = ('employee__employee_code',)
