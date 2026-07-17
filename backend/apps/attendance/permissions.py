"""Role groups and permission helpers for attendance management."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    'Super Admin': {
        'shift': ('add', 'change', 'delete', 'view'),
        'holiday': ('add', 'change', 'delete', 'view'),
        'attendanceperiod': ('add', 'change', 'delete', 'view', 'reopen'),
        'attendance': ('add', 'change', 'delete', 'view'),
        'weeklyoff': ('add', 'change', 'delete', 'view'),
        'shiftassignment': ('add', 'change', 'delete', 'view'),
        'attendancemonthlysummary': ('add', 'change', 'delete', 'view'),
    },
    'Admin': {
        'shift': ('add', 'change', 'delete', 'view'),
        'holiday': ('add', 'change', 'delete', 'view'),
        'attendanceperiod': ('add', 'change', 'delete', 'view', 'reopen'),
        'attendance': ('add', 'change', 'delete', 'view'),
        'weeklyoff': ('add', 'change', 'delete', 'view'),
        'shiftassignment': ('add', 'change', 'delete', 'view'),
        'attendancemonthlysummary': ('add', 'change', 'delete', 'view'),
    },
    'HR': {
        'shift': ('add', 'change', 'view'),
        'holiday': ('add', 'change', 'view'),
        'attendanceperiod': ('add', 'change', 'view', 'reopen'),
        'attendance': ('add', 'change', 'view'),
        'weeklyoff': ('add', 'change', 'view'),
        'shiftassignment': ('add', 'change', 'view'),
        'attendancemonthlysummary': ('view',),
    },
    'Payroll': {
        'shift': ('view',),
        'holiday': ('view',),
        'attendanceperiod': ('view', 'change'),
        'attendance': ('view', 'change'),
        'weeklyoff': ('view',),
        'shiftassignment': ('view',),
        'attendancemonthlysummary': ('view', 'change', 'add'),
    },
    'Viewer': {
        'shift': ('view',),
        'holiday': ('view',),
        'attendanceperiod': ('view',),
        'attendance': ('view',),
        'weeklyoff': ('view',),
        'shiftassignment': ('view',),
        'attendancemonthlysummary': ('view',),
    },
}

VIEW_SHIFT = 'attendance.view_shift'
ADD_SHIFT = 'attendance.add_shift'
CHANGE_SHIFT = 'attendance.change_shift'
DELETE_SHIFT = 'attendance.delete_shift'

VIEW_HOLIDAY = 'attendance.view_holiday'
ADD_HOLIDAY = 'attendance.add_holiday'
CHANGE_HOLIDAY = 'attendance.change_holiday'
DELETE_HOLIDAY = 'attendance.delete_holiday'

VIEW_PERIOD = 'attendance.view_attendanceperiod'
ADD_PERIOD = 'attendance.add_attendanceperiod'
CHANGE_PERIOD = 'attendance.change_attendanceperiod'
DELETE_PERIOD = 'attendance.delete_attendanceperiod'
REOPEN_PERIOD = 'attendance.reopen_attendanceperiod'

VIEW_ATTENDANCE = 'attendance.view_attendance'
ADD_ATTENDANCE = 'attendance.add_attendance'
CHANGE_ATTENDANCE = 'attendance.change_attendance'
DELETE_ATTENDANCE = 'attendance.delete_attendance'

VIEW_WEEKLY_OFF = 'attendance.view_weeklyoff'
ADD_WEEKLY_OFF = 'attendance.add_weeklyoff'
CHANGE_WEEKLY_OFF = 'attendance.change_weeklyoff'
DELETE_WEEKLY_OFF = 'attendance.delete_weeklyoff'

VIEW_SUMMARY = 'attendance.view_attendancemonthlysummary'


def seed_role_groups():
    """Merge attendance permissions into existing PAS role groups."""
    from .models import (
        Attendance,
        AttendanceMonthlySummary,
        AttendancePeriod,
        Holiday,
        Shift,
        ShiftAssignment,
        WeeklyOff,
    )

    model_map = {
        'shift': Shift,
        'holiday': Holiday,
        'attendanceperiod': AttendancePeriod,
        'attendance': Attendance,
        'weeklyoff': WeeklyOff,
        'shiftassignment': ShiftAssignment,
        'attendancemonthlysummary': AttendanceMonthlySummary,
    }

    for group_name, model_perms in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        existing = list(group.permissions.all())
        permissions = list(existing)
        for model_key, actions in model_perms.items():
            content_type = ContentType.objects.get_for_model(model_map[model_key])
            for action in actions:
                codename = f'{action}_{model_key}'
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                except Permission.DoesNotExist:
                    continue
                if perm not in permissions:
                    permissions.append(perm)
        group.permissions.set(permissions)
    return list(ROLE_GROUPS.keys())
