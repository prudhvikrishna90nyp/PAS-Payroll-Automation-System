from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from apps.common.mixins import BaseModel, SoftDeleteModel
from apps.company.models import Company
from apps.employee.models import Employee


class HolidayType(models.TextChoices):
    NATIONAL = 'national', 'National'
    FESTIVAL = 'festival', 'Festival'
    OPTIONAL = 'optional', 'Optional'
    COMPANY = 'company', 'Company'
    REGIONAL = 'regional', 'Regional'


class PeriodStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    LOCKED = 'locked', 'Locked'
    PROCESSED = 'processed', 'Processed'


class AttendanceStatus(models.TextChoices):
    PRESENT = 'P', 'Present'
    ABSENT = 'A', 'Absent'
    HOLIDAY = 'H', 'Holiday'
    WEEKLY_OFF = 'WO', 'Weekly Off'
    CASUAL_LEAVE = 'CL', 'Casual Leave'
    SICK_LEAVE = 'SL', 'Sick Leave'
    EARNED_LEAVE = 'EL', 'Earned Leave'
    LOP = 'LOP', 'Loss of Pay'
    HALF_DAY = 'HD', 'Half Day'
    ON_DUTY = 'OD', 'On Duty'


class Weekday(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'


class Shift(SoftDeleteModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='shifts',
    )
    shift_code = models.CharField(max_length=20)
    shift_name = models.CharField(max_length=100)
    in_time = models.TimeField()
    out_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=60)
    grace_in_minutes = models.PositiveIntegerField(default=10)
    grace_out_minutes = models.PositiveIntegerField(default=10)
    half_day_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('4.00'),
    )
    full_day_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('8.00'),
    )
    is_night_shift = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_shift_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_shift_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['company__company_name', 'shift_code']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'shift_code'],
                name='uniq_shift_company_code',
            ),
        ]

    def __str__(self):
        return f'{self.shift_code} — {self.shift_name}'

    def save(self, *args, **kwargs):
        self.shift_code = self.shift_code.strip().upper()
        self.shift_name = self.shift_name.strip()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('attendance:shift_detail', kwargs={'pk': self.pk})


class Holiday(SoftDeleteModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='holidays',
    )
    holiday_date = models.DateField()
    holiday_name = models.CharField(max_length=200)
    holiday_type = models.CharField(
        max_length=20,
        choices=HolidayType.choices,
        default=HolidayType.NATIONAL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_holiday_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_holiday_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-holiday_date', 'holiday_name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'holiday_date', 'holiday_name'],
                name='uniq_holiday_company_date_name',
            ),
        ]

    def __str__(self):
        return f'{self.holiday_date} — {self.holiday_name}'

    def get_absolute_url(self):
        return reverse('attendance:holiday_detail', kwargs={'pk': self.pk})


class AttendancePeriod(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='attendance_periods',
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_period_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_period_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-year', '-month', 'company__company_name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'month', 'year'],
                name='uniq_attendance_period_company_month_year',
            ),
        ]
        permissions = [
            ('reopen_attendanceperiod', 'Can reopen locked attendance period'),
        ]

    def __str__(self):
        return f'{self.company.company_name} — {self.month:02d}/{self.year} ({self.get_status_display()})'

    def clean(self):
        if self.month < 1 or self.month > 12:
            raise ValidationError({'month': 'Month must be between 1 and 12.'})
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'End date must be on or after start date.'})

    @property
    def is_editable(self):
        return self.status == PeriodStatus.OPEN

    def get_absolute_url(self):
        return reverse('attendance:period_detail', kwargs={'pk': self.pk})


class Attendance(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_days',
    )
    attendance_date = models.DateField()
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_days',
    )
    status = models.CharField(
        max_length=5,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    worked_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    late_minutes = models.PositiveIntegerField(default=0)
    early_exit_minutes = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-attendance_date', 'employee__employee_code']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'attendance_date'],
                name='uniq_attendance_employee_date',
            ),
        ]
        verbose_name_plural = 'attendance'

    def __str__(self):
        return f'{self.employee.employee_code} — {self.attendance_date} ({self.status})'

    def get_absolute_url(self):
        return reverse('attendance:attendance_detail', kwargs={'pk': self.pk})

    @property
    def company(self):
        return self.employee.company


class WeeklyOff(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='weekly_offs',
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_weeklyoff_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_weeklyoff_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['employee__employee_code', 'weekday', 'effective_from']
        verbose_name = 'weekly off'
        verbose_name_plural = 'weekly offs'

    def __str__(self):
        return f'{self.employee.employee_code} — {self.get_weekday_display()}'

    def clean(self):
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            raise ValidationError({'effective_to': 'Effective to must be on or after effective from.'})


class ShiftAssignment(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='shift_assignments',
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_shiftassignment_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_shiftassignment_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['employee__employee_code', '-effective_from']

    def __str__(self):
        return f'{self.employee.employee_code} → {self.shift.shift_code}'

    def clean(self):
        if self.shift_id and self.employee_id and self.shift.company_id != self.employee.company_id:
            raise ValidationError('Shift must belong to the employee company.')
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            raise ValidationError({'effective_to': 'Effective to must be on or after effective from.'})


class AttendanceMonthlySummary(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_monthly_summaries',
    )
    period = models.ForeignKey(
        AttendancePeriod,
        on_delete=models.CASCADE,
        related_name='monthly_summaries',
    )
    present_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    absent_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    paid_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    weekly_off_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    holiday_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    half_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    late_count = models.PositiveIntegerField(default=0)
    lop_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_monthlysummary_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='attendance_monthlysummary_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-period__year', '-period__month', 'employee__employee_code']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'period'],
                name='uniq_attendance_monthly_summary_employee_period',
            ),
        ]
        verbose_name_plural = 'attendance monthly summaries'

    def __str__(self):
        return f'{self.employee.employee_code} — {self.period.month:02d}/{self.period.year}'
