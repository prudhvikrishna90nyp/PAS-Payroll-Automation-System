from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.company.models import Company
from apps.employee.models import Employee

from .models import (
    Attendance,
    AttendancePeriod,
    Holiday,
    PeriodStatus,
    Shift,
    ShiftAssignment,
    WeeklyOff,
)
from .services import assert_period_editable, calculate_attendance_metrics, resolve_shift_for_employee


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            elif isinstance(widget, (forms.Textarea,)):
                widget.attrs.setdefault('class', 'form-control')
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs.setdefault('class', 'form-control')


class ShiftForm(BootstrapModelForm):
    class Meta:
        model = Shift
        fields = [
            'company',
            'shift_code',
            'shift_name',
            'in_time',
            'out_time',
            'break_minutes',
            'grace_in_minutes',
            'grace_out_minutes',
            'half_day_hours',
            'full_day_hours',
            'is_night_shift',
            'is_active',
        ]
        widgets = {
            'in_time': forms.TimeInput(attrs={'type': 'time'}),
            'out_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')


class HolidayForm(BootstrapModelForm):
    class Meta:
        model = Holiday
        fields = ['company', 'holiday_date', 'holiday_name', 'holiday_type', 'is_active']
        widgets = {
            'holiday_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')


class AttendancePeriodForm(BootstrapModelForm):
    class Meta:
        model = AttendancePeriod
        fields = ['company', 'month', 'year', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')
        if self.instance and self.instance.pk and self.instance.status != PeriodStatus.OPEN:
            self.fields['status'].disabled = True


class PeriodTransitionForm(forms.Form):
    status = forms.ChoiceField(
        choices=PeriodStatus.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class AttendanceForm(BootstrapModelForm):
    class Meta:
        model = Attendance
        fields = [
            'employee',
            'attendance_date',
            'shift',
            'status',
            'check_in',
            'check_out',
            'worked_hours',
            'overtime_hours',
            'late_minutes',
            'early_exit_minutes',
            'remarks',
            'approved',
        ]
        widgets = {
            'attendance_date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).select_related(
            'company'
        ).order_by('employee_code')
        company = None
        if self.data.get('employee'):
            try:
                company = Employee.objects.get(pk=self.data.get('employee')).company
            except (Employee.DoesNotExist, ValueError, TypeError):
                company = None
        elif self.instance and self.instance.pk:
            company = self.instance.employee.company
        if company:
            self.fields['shift'].queryset = Shift.objects.filter(company=company, is_active=True)
        else:
            self.fields['shift'].queryset = Shift.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        employee = cleaned.get('employee')
        attendance_date = cleaned.get('attendance_date')
        shift = cleaned.get('shift')
        check_in = cleaned.get('check_in')
        check_out = cleaned.get('check_out')

        if employee and attendance_date:
            try:
                assert_period_editable(employee.company, attendance_date, self.user)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages if hasattr(exc, 'messages') else [str(exc)])

        if shift and employee and shift.company_id != employee.company_id:
            self.add_error('shift', 'Shift must belong to the employee company.')

        if check_in and check_out and not shift and employee and attendance_date:
            cleaned['shift'] = resolve_shift_for_employee(employee, attendance_date)

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.shift_id and instance.employee_id and instance.attendance_date:
            instance.shift = resolve_shift_for_employee(instance.employee, instance.attendance_date)
        calculate_attendance_metrics(instance)
        if commit:
            instance.save()
        return instance


class WeeklyOffForm(BootstrapModelForm):
    class Meta:
        model = WeeklyOff
        fields = ['employee', 'weekday', 'effective_from', 'effective_to', 'is_active']
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
            'effective_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).order_by(
            'employee_code'
        )


class ShiftAssignmentForm(BootstrapModelForm):
    class Meta:
        model = ShiftAssignment
        fields = ['employee', 'shift', 'effective_from', 'effective_to', 'is_active']
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
            'effective_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).order_by(
            'employee_code'
        )
        self.fields['shift'].queryset = Shift.objects.filter(is_active=True).order_by('shift_code')


class AttendanceImportForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by('company_name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
        help_text='Excel (.xlsx) with columns: Employee Code, Date, In, Out, Status, OT',
    )

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        name = (uploaded.name or '').lower()
        if not name.endswith('.xlsx'):
            raise forms.ValidationError('Please upload an .xlsx Excel file.')
        return uploaded
