from datetime import date, time
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from apps.clients.models import Client
from apps.company.models import Company
from apps.employee.models import Employee

from .import_export import import_attendance
from .models import (
    Attendance,
    AttendanceMonthlySummary,
    AttendancePeriod,
    AttendanceStatus,
    Holiday,
    HolidayType,
    PeriodStatus,
    Shift,
    WeeklyOff,
)
from .permissions import ROLE_GROUPS, seed_role_groups
from .services import generate_monthly_summaries, transition_period


def _attendance_permission(codename):
    return Permission.objects.get(codename=codename, content_type__app_label='attendance')


class AttendanceTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='attadmin',
            password='TestPassword123!',
        )
        for codename in (
            'view_shift',
            'add_shift',
            'change_shift',
            'delete_shift',
            'view_holiday',
            'add_holiday',
            'change_holiday',
            'delete_holiday',
            'view_attendanceperiod',
            'add_attendanceperiod',
            'change_attendanceperiod',
            'delete_attendanceperiod',
            'reopen_attendanceperiod',
            'view_attendance',
            'add_attendance',
            'change_attendance',
            'delete_attendance',
            'view_weeklyoff',
            'add_weeklyoff',
            'change_weeklyoff',
            'delete_weeklyoff',
            'view_shiftassignment',
            'add_shiftassignment',
            'view_attendancemonthlysummary',
        ):
            try:
                self.user.user_permissions.add(_attendance_permission(codename))
            except Permission.DoesNotExist:
                pass

        self.client_record = Client.objects.create(
            client_code='ATTCLI',
            client_name='Attendance Client',
            mobile='9876543210',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='Attendance Co',
        )
        self.employee = Employee.objects.create(
            company=self.company,
            employee_code='EMP9001',
            first_name='Asha',
            last_name='Rao',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('30000.00'),
            auto_generate_code=False,
        )
        self.shift = Shift.objects.create(
            company=self.company,
            shift_code='GEN',
            shift_name='General',
            in_time=time(9, 0),
            out_time=time(18, 0),
            break_minutes=60,
            grace_in_minutes=10,
            grace_out_minutes=10,
            half_day_hours=Decimal('4.00'),
            full_day_hours=Decimal('8.00'),
        )
        self.period = AttendancePeriod.objects.create(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            status=PeriodStatus.OPEN,
        )


class AttendanceModelTests(AttendanceTestMixin, TestCase):
    def test_shift_unique_code_per_company(self):
        with self.assertRaises(Exception):
            Shift.objects.create(
                company=self.company,
                shift_code='gen',
                shift_name='Duplicate',
                in_time=time(10, 0),
                out_time=time(19, 0),
            )

    def test_attendance_unique_employee_date(self):
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 1),
            status=AttendanceStatus.PRESENT,
            shift=self.shift,
        )
        with self.assertRaises(Exception):
            Attendance.objects.create(
                employee=self.employee,
                attendance_date=date(2026, 7, 1),
                status=AttendanceStatus.ABSENT,
            )

    def test_holiday_and_weekly_off(self):
        holiday = Holiday.objects.create(
            company=self.company,
            holiday_date=date(2026, 8, 15),
            holiday_name='Independence Day',
            holiday_type=HolidayType.NATIONAL,
        )
        weekly = WeeklyOff.objects.create(
            employee=self.employee,
            weekday=6,
            effective_from=date(2026, 1, 1),
        )
        self.assertEqual(str(holiday), '2026-08-15 — Independence Day')
        self.assertIn('Sunday', str(weekly))


class AttendancePeriodLockTests(AttendanceTestMixin, TestCase):
    def test_lock_blocks_attendance_edit(self):
        from .services import assert_period_editable

        transition_period(self.period, PeriodStatus.LOCKED, self.user)
        with self.assertRaises(ValidationError):
            assert_period_editable(self.company, date(2026, 7, 5), self.user)

    def test_reopen_requires_permission(self):
        transition_period(self.period, PeriodStatus.LOCKED, self.user)
        limited = get_user_model().objects.create_user(username='nolock', password='x')
        limited.user_permissions.add(_attendance_permission('change_attendanceperiod'))
        with self.assertRaises(Exception):
            transition_period(self.period, PeriodStatus.OPEN, limited)

    def test_reopen_with_permission(self):
        transition_period(self.period, PeriodStatus.LOCKED, self.user)
        transition_period(self.period, PeriodStatus.OPEN, self.user)
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, PeriodStatus.OPEN)

    def test_lock_generates_monthly_summary(self):
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 2),
            status=AttendanceStatus.PRESENT,
            overtime_hours=Decimal('1.50'),
        )
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 3),
            status=AttendanceStatus.ABSENT,
        )
        transition_period(self.period, PeriodStatus.LOCKED, self.user)
        summary = AttendanceMonthlySummary.objects.get(employee=self.employee, period=self.period)
        self.assertEqual(summary.present_days, Decimal('1.00'))
        self.assertEqual(summary.absent_days, Decimal('1.00'))
        self.assertEqual(summary.overtime_hours, Decimal('1.50'))


class AttendanceImportTests(AttendanceTestMixin, TestCase):
    def _workbook(self, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Employee Code', 'Date', 'In', 'Out', 'Status', 'OT'])
        for row in rows:
            sheet.append(row)
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    def test_import_creates_rows(self):
        uploaded = self._workbook([
            ['EMP9001', '2026-07-10', '09:00', '18:00', 'P', '0.5'],
        ])
        created, updated, skipped, errors = import_attendance(self.company, uploaded, self.user)
        self.assertEqual(created, 1)
        self.assertEqual(errors, [])
        record = Attendance.objects.get(employee=self.employee, attendance_date=date(2026, 7, 10))
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertEqual(record.overtime_hours, Decimal('0.50'))

    def test_import_rejects_unknown_employee(self):
        uploaded = self._workbook([
            ['UNKNOWN', '2026-07-10', '09:00', '18:00', 'P', '0'],
        ])
        created, updated, skipped, errors = import_attendance(self.company, uploaded, self.user)
        self.assertEqual(created, 0)
        self.assertTrue(any('Employee not found' in e for e in errors))

    def test_import_rejects_locked_period(self):
        transition_period(self.period, PeriodStatus.LOCKED, self.user)
        uploaded = self._workbook([
            ['EMP9001', '2026-07-10', '09:00', '18:00', 'P', '0'],
        ])
        created, updated, skipped, errors = import_attendance(self.company, uploaded, self.user)
        self.assertEqual(created, 0)
        self.assertTrue(any('Locked' in e or 'locked' in e for e in errors))

    def test_import_invalid_status(self):
        uploaded = self._workbook([
            ['EMP9001', '2026-07-10', '09:00', '18:00', 'XYZ', '0'],
        ])
        _, _, _, errors = import_attendance(self.company, uploaded, self.user)
        self.assertTrue(any('Invalid status' in e for e in errors))


class AttendanceViewTests(AttendanceTestMixin, TestCase):
    def test_login_required(self):
        response = self.client.get(reverse('attendance:attendance_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_list_and_create(self):
        self.client.login(username='attadmin', password='TestPassword123!')
        response = self.client.get(reverse('attendance:attendance_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('attendance:attendance_add'),
            {
                'employee': self.employee.pk,
                'attendance_date': '2026-07-12',
                'shift': self.shift.pk,
                'status': AttendanceStatus.PRESENT,
                'check_in': '09:05',
                'check_out': '18:00',
                'worked_hours': '0',
                'overtime_hours': '0',
                'late_minutes': '0',
                'early_exit_minutes': '0',
                'remarks': '',
                'approved': False,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Attendance.objects.filter(employee=self.employee, attendance_date=date(2026, 7, 12)).exists()
        )

    def test_shift_and_holiday_crud(self):
        self.client.login(username='attadmin', password='TestPassword123!')
        response = self.client.get(reverse('attendance:shift_list'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse('attendance:holiday_add'),
            {
                'company': self.company.pk,
                'holiday_date': '2026-10-02',
                'holiday_name': 'Gandhi Jayanti',
                'holiday_type': HolidayType.NATIONAL,
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Holiday.objects.filter(holiday_name='Gandhi Jayanti').exists())

    def test_period_transition_view(self):
        self.client.login(username='attadmin', password='TestPassword123!')
        response = self.client.post(
            reverse('attendance:period_transition', kwargs={'pk': self.period.pk}),
            {'status': PeriodStatus.LOCKED},
        )
        self.assertEqual(response.status_code, 302)
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, PeriodStatus.LOCKED)

    def test_import_view(self):
        self.client.login(username='attadmin', password='TestPassword123!')
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Employee Code', 'Date', 'In', 'Out', 'Status', 'OT'])
        sheet.append(['EMP9001', '2026-07-15', '09:00', '18:00', 'P', '0'])
        buffer = BytesIO()
        workbook.save(buffer)
        uploaded = SimpleUploadedFile(
            'att.xlsx',
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response = self.client.post(
            reverse('attendance:attendance_import'),
            {'company': self.company.pk, 'file': uploaded},
        )
        self.assertIn(response.status_code, (200, 302))
        self.assertTrue(
            Attendance.objects.filter(employee=self.employee, attendance_date=date(2026, 7, 15)).exists()
        )

    def test_daily_report_download(self):
        self.client.login(username='attadmin', password='TestPassword123!')
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 8),
            status=AttendanceStatus.PRESENT,
        )
        response = self.client.get(reverse('attendance:report_download', kwargs={'report_type': 'daily'}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            response['Content-Type'],
        )

    def test_viewer_cannot_add(self):
        viewer = get_user_model().objects.create_user(username='viewer', password='TestPassword123!')
        viewer.user_permissions.add(_attendance_permission('view_attendance'))
        self.client.login(username='viewer', password='TestPassword123!')
        response = self.client.get(reverse('attendance:attendance_add'))
        self.assertEqual(response.status_code, 403)


class AttendanceRoleSeedTests(TestCase):
    def test_seed_role_groups_includes_attendance(self):
        seed_role_groups()
        admin = Group.objects.get(name='Admin')
        self.assertTrue(admin.permissions.filter(codename='view_attendance').exists())
        self.assertTrue(admin.permissions.filter(codename='reopen_attendanceperiod').exists())
        self.assertEqual(set(ROLE_GROUPS.keys()), {'Super Admin', 'Admin', 'HR', 'Payroll', 'Viewer'})


class MonthlySummaryServiceTests(AttendanceTestMixin, TestCase):
    def test_generate_monthly_summaries(self):
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 4),
            status=AttendanceStatus.HALF_DAY,
        )
        Attendance.objects.create(
            employee=self.employee,
            attendance_date=date(2026, 7, 5),
            status=AttendanceStatus.LOP,
        )
        summaries = generate_monthly_summaries(self.period, user=self.user)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].half_days, Decimal('1.00'))
        self.assertEqual(summaries[0].lop_days, Decimal('1.00'))
        self.assertEqual(summaries[0].present_days, Decimal('0.50'))
