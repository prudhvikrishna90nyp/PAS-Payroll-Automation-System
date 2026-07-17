from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.clients.models import Client
from apps.company.models import Company
from apps.employee.models import Employee

from .filters import (
    attendance_list_queryset,
    holiday_list_queryset,
    period_list_queryset,
    shift_list_queryset,
)
from .forms import (
    AttendanceForm,
    AttendanceImportForm,
    AttendancePeriodForm,
    HolidayForm,
    PeriodTransitionForm,
    ShiftAssignmentForm,
    ShiftForm,
    WeeklyOffForm,
)
from .import_export import (
    export_attendance,
    export_attendance_template,
    export_import_errors,
    import_attendance,
)
from .models import (
    Attendance,
    AttendancePeriod,
    AttendanceStatus,
    Holiday,
    HolidayType,
    PeriodStatus,
    Shift,
    ShiftAssignment,
    WeeklyOff,
)
from .permissions import (
    ADD_ATTENDANCE,
    ADD_HOLIDAY,
    ADD_PERIOD,
    ADD_SHIFT,
    ADD_WEEKLY_OFF,
    CHANGE_ATTENDANCE,
    CHANGE_HOLIDAY,
    CHANGE_PERIOD,
    CHANGE_SHIFT,
    CHANGE_WEEKLY_OFF,
    DELETE_ATTENDANCE,
    DELETE_HOLIDAY,
    DELETE_PERIOD,
    DELETE_SHIFT,
    DELETE_WEEKLY_OFF,
    REOPEN_PERIOD,
    VIEW_ATTENDANCE,
    VIEW_HOLIDAY,
    VIEW_PERIOD,
    VIEW_SHIFT,
    VIEW_WEEKLY_OFF,
)
from .reports import REPORT_BUILDERS
from .services import generate_monthly_summaries, transition_period


class AttendanceLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Require authentication and an attendance model permission."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class AttendanceNavMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendance_nav'] = True
        return context


# ---- Shift ----

class ShiftListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = Shift
    template_name = 'attendance/shift_list.html'
    context_object_name = 'shifts'
    paginate_by = 15
    permission_required = VIEW_SHIFT

    def get_queryset(self):
        return shift_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class ShiftDetailView(AttendanceLoginPermissionMixin, AttendanceNavMixin, DetailView):
    model = Shift
    template_name = 'attendance/shift_detail.html'
    context_object_name = 'shift'
    permission_required = VIEW_SHIFT


class ShiftCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'attendance/shift_form.html'
    success_url = reverse_lazy('attendance:shift_list')
    permission_required = ADD_SHIFT

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Shift created successfully.')
        return super().form_valid(form)


class ShiftUpdateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'attendance/shift_form.html'
    success_url = reverse_lazy('attendance:shift_list')
    permission_required = CHANGE_SHIFT

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Shift updated successfully.')
        return super().form_valid(form)


class ShiftArchiveView(AttendanceLoginPermissionMixin, View):
    permission_required = DELETE_SHIFT

    def post(self, request, pk):
        shift = get_object_or_404(Shift, pk=pk)
        shift.soft_delete()
        shift.updated_by = request.user
        shift.save(update_fields=['updated_by', 'updated_at'])
        messages.success(request, f'Shift {shift.shift_code} archived.')
        return redirect('attendance:shift_list')


# ---- Holiday ----

class HolidayListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = Holiday
    template_name = 'attendance/holiday_list.html'
    context_object_name = 'holidays'
    paginate_by = 20
    permission_required = VIEW_HOLIDAY

    def get_queryset(self):
        return holiday_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['year_filter'] = self.request.GET.get('year', '')
        context['holiday_type_filter'] = self.request.GET.get('holiday_type', '')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['holiday_types'] = HolidayType.choices
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class HolidayDetailView(AttendanceLoginPermissionMixin, AttendanceNavMixin, DetailView):
    model = Holiday
    template_name = 'attendance/holiday_detail.html'
    context_object_name = 'holiday'
    permission_required = VIEW_HOLIDAY


class HolidayCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = Holiday
    form_class = HolidayForm
    template_name = 'attendance/holiday_form.html'
    success_url = reverse_lazy('attendance:holiday_list')
    permission_required = ADD_HOLIDAY

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Holiday created successfully.')
        return super().form_valid(form)


class HolidayUpdateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, UpdateView):
    model = Holiday
    form_class = HolidayForm
    template_name = 'attendance/holiday_form.html'
    success_url = reverse_lazy('attendance:holiday_list')
    permission_required = CHANGE_HOLIDAY

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Holiday updated successfully.')
        return super().form_valid(form)


class HolidayArchiveView(AttendanceLoginPermissionMixin, View):
    permission_required = DELETE_HOLIDAY

    def post(self, request, pk):
        holiday = get_object_or_404(Holiday, pk=pk)
        holiday.soft_delete()
        messages.success(request, f'Holiday {holiday.holiday_name} archived.')
        return redirect('attendance:holiday_list')


# ---- Period ----

class PeriodListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = AttendancePeriod
    template_name = 'attendance/period_list.html'
    context_object_name = 'periods'
    paginate_by = 15
    permission_required = VIEW_PERIOD

    def get_queryset(self):
        return period_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_filter'] = self.request.GET.get('company', '')
        context['year_filter'] = self.request.GET.get('year', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['period_statuses'] = PeriodStatus.choices
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class PeriodDetailView(AttendanceLoginPermissionMixin, AttendanceNavMixin, DetailView):
    model = AttendancePeriod
    template_name = 'attendance/period_detail.html'
    context_object_name = 'period'
    permission_required = VIEW_PERIOD

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transition_form'] = PeriodTransitionForm(initial={'status': self.object.status})
        context['can_reopen'] = self.request.user.has_perm(REOPEN_PERIOD)
        context['can_change'] = self.request.user.has_perm(CHANGE_PERIOD)
        return context


class PeriodCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = AttendancePeriod
    form_class = AttendancePeriodForm
    template_name = 'attendance/period_form.html'
    success_url = reverse_lazy('attendance:period_list')
    permission_required = ADD_PERIOD

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Attendance period created successfully.')
        return super().form_valid(form)


class PeriodUpdateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, UpdateView):
    model = AttendancePeriod
    form_class = AttendancePeriodForm
    template_name = 'attendance/period_form.html'
    success_url = reverse_lazy('attendance:period_list')
    permission_required = CHANGE_PERIOD

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Attendance period updated successfully.')
        return super().form_valid(form)


class PeriodTransitionView(AttendanceLoginPermissionMixin, View):
    permission_required = CHANGE_PERIOD

    def post(self, request, pk):
        period = get_object_or_404(AttendancePeriod, pk=pk)
        form = PeriodTransitionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Invalid period status.')
            return redirect('attendance:period_detail', pk=pk)
        try:
            transition_period(period, form.cleaned_data['status'], request.user)
            messages.success(request, f'Period status set to {period.get_status_display()}.')
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
        return redirect('attendance:period_detail', pk=pk)


class PeriodGenerateSummaryView(AttendanceLoginPermissionMixin, View):
    permission_required = CHANGE_PERIOD

    def post(self, request, pk):
        period = get_object_or_404(AttendancePeriod, pk=pk)
        summaries = generate_monthly_summaries(period, user=request.user)
        messages.success(request, f'Generated {len(summaries)} monthly summary row(s).')
        return redirect('attendance:period_detail', pk=pk)


class PeriodDeleteView(AttendanceLoginPermissionMixin, View):
    permission_required = DELETE_PERIOD

    def post(self, request, pk):
        period = get_object_or_404(AttendancePeriod, pk=pk)
        if period.status != PeriodStatus.OPEN:
            messages.error(request, 'Only open periods can be deleted.')
            return redirect('attendance:period_detail', pk=pk)
        period.delete()
        messages.success(request, 'Attendance period deleted.')
        return redirect('attendance:period_list')


# ---- Daily Attendance ----

class AttendanceListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = Attendance
    template_name = 'attendance/attendance_list.html'
    context_object_name = 'records'
    paginate_by = 20
    permission_required = VIEW_ATTENDANCE

    def get_queryset(self):
        return attendance_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['client_filter'] = self.request.GET.get('client', '')
        context['employee_filter'] = self.request.GET.get('employee', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['period_filter'] = self.request.GET.get('period', '')
        context['clients'] = Client.objects.filter(is_active=True).order_by('client_name')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['employees'] = Employee.objects.filter(is_active=True).order_by('employee_code')[:500]
        context['periods'] = AttendancePeriod.objects.select_related('company').order_by(
            '-year', '-month'
        )[:100]
        context['statuses'] = AttendanceStatus.choices
        context['employee_count'] = Employee.objects.filter(is_active=True).count()
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class AttendanceDetailView(AttendanceLoginPermissionMixin, AttendanceNavMixin, DetailView):
    model = Attendance
    template_name = 'attendance/attendance_detail.html'
    context_object_name = 'record'
    permission_required = VIEW_ATTENDANCE

    def get_queryset(self):
        return Attendance.objects.select_related(
            'employee',
            'employee__company',
            'shift',
            'created_by',
            'updated_by',
        )


class AttendanceCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'attendance/attendance_form.html'
    success_url = reverse_lazy('attendance:attendance_list')
    permission_required = ADD_ATTENDANCE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            messages.error(self.request, 'Could not save attendance.')
            return self.form_invalid(form)
        messages.success(self.request, 'Attendance saved successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class AttendanceUpdateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'attendance/attendance_form.html'
    success_url = reverse_lazy('attendance:attendance_list')
    permission_required = CHANGE_ATTENDANCE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            messages.error(self.request, 'Could not update attendance.')
            return self.form_invalid(form)
        messages.success(self.request, 'Attendance updated successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class AttendanceDeleteView(AttendanceLoginPermissionMixin, View):
    permission_required = DELETE_ATTENDANCE

    def post(self, request, pk):
        record = get_object_or_404(Attendance, pk=pk)
        from .services import assert_period_editable

        try:
            assert_period_editable(record.employee.company, record.attendance_date, request.user)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
            return redirect('attendance:attendance_detail', pk=pk)
        record.delete()
        messages.success(request, 'Attendance record deleted.')
        return redirect('attendance:attendance_list')


class AttendanceExportView(AttendanceLoginPermissionMixin, View):
    permission_required = VIEW_ATTENDANCE

    def get(self, request):
        if request.GET.get('template') == '1':
            return export_attendance_template()
        return export_attendance(attendance_list_queryset(request.GET))


class AttendanceImportView(AttendanceLoginPermissionMixin, AttendanceNavMixin, View):
    template_name = 'attendance/attendance_import.html'
    success_url = reverse_lazy('attendance:attendance_list')
    permission_required = ADD_ATTENDANCE

    def get(self, request):
        return render(request, self.template_name, {'form': AttendanceImportForm()})

    def post(self, request):
        if request.POST.get('download_errors') and request.session.get('attendance_import_errors'):
            return export_import_errors(request.session['attendance_import_errors'])

        form = AttendanceImportForm(request.POST, request.FILES)
        if form.is_valid():
            created, updated, skipped, errors = import_attendance(
                form.cleaned_data['company'],
                form.cleaned_data['file'],
                request.user,
            )
            if created:
                messages.success(request, f'{created} attendance row(s) created.')
            if updated:
                messages.success(request, f'{updated} attendance row(s) updated.')
            if skipped and not errors:
                messages.info(request, f'{skipped} row(s) skipped.')
            if errors:
                request.session['attendance_import_errors'] = errors
                messages.warning(
                    request,
                    f'{len(errors)} row(s) had issues. Download the error log for details.',
                )
            elif created or updated:
                request.session.pop('attendance_import_errors', None)
                return redirect(self.success_url)
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'import_errors': errors,
                    'created_count': created,
                    'updated_count': updated,
                    'skipped_count': skipped,
                },
            )
        messages.error(request, 'Please upload a valid Excel file.')
        return render(request, self.template_name, {'form': form})


class AttendanceReportIndexView(AttendanceLoginPermissionMixin, AttendanceNavMixin, View):
    permission_required = VIEW_ATTENDANCE
    template_name = 'attendance/report_index.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                'companies': Company.objects.filter(is_active=True).order_by('company_name'),
                'periods': AttendancePeriod.objects.select_related('company').order_by(
                    '-year', '-month'
                )[:100],
                'company_filter': request.GET.get('company', ''),
                'period_filter': request.GET.get('period', ''),
                'date_from': request.GET.get('date_from', ''),
                'date_to': request.GET.get('date_to', ''),
                'year_filter': request.GET.get('year', ''),
            },
        )


class AttendanceReportDownloadView(AttendanceLoginPermissionMixin, View):
    permission_required = VIEW_ATTENDANCE

    def get(self, request, report_type):
        builder = REPORT_BUILDERS.get(report_type)
        if builder is None:
            messages.error(request, 'Unknown report type.')
            return redirect('attendance:report_index')
        return builder(request.GET)


# ---- Weekly Off / Shift Assignment ----

class WeeklyOffListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = WeeklyOff
    template_name = 'attendance/weeklyoff_list.html'
    context_object_name = 'weekly_offs'
    paginate_by = 20
    permission_required = VIEW_WEEKLY_OFF

    def get_queryset(self):
        qs = WeeklyOff.objects.select_related('employee', 'employee__company')
        company = self.request.GET.get('company')
        if company:
            qs = qs.filter(employee__company_id=company)
        return qs


class WeeklyOffCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = WeeklyOff
    form_class = WeeklyOffForm
    template_name = 'attendance/weeklyoff_form.html'
    success_url = reverse_lazy('attendance:weeklyoff_list')
    permission_required = ADD_WEEKLY_OFF

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Weekly off saved.')
        return super().form_valid(form)


class WeeklyOffUpdateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, UpdateView):
    model = WeeklyOff
    form_class = WeeklyOffForm
    template_name = 'attendance/weeklyoff_form.html'
    success_url = reverse_lazy('attendance:weeklyoff_list')
    permission_required = CHANGE_WEEKLY_OFF

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Weekly off updated.')
        return super().form_valid(form)


class WeeklyOffDeleteView(AttendanceLoginPermissionMixin, View):
    permission_required = DELETE_WEEKLY_OFF

    def post(self, request, pk):
        obj = get_object_or_404(WeeklyOff, pk=pk)
        obj.delete()
        messages.success(request, 'Weekly off deleted.')
        return redirect('attendance:weeklyoff_list')


class ShiftAssignmentListView(AttendanceLoginPermissionMixin, AttendanceNavMixin, ListView):
    model = ShiftAssignment
    template_name = 'attendance/shiftassignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    permission_required = VIEW_SHIFT

    def get_queryset(self):
        qs = ShiftAssignment.objects.select_related('employee', 'shift', 'employee__company')
        company = self.request.GET.get('company')
        if company:
            qs = qs.filter(employee__company_id=company)
        return qs


class ShiftAssignmentCreateView(AttendanceLoginPermissionMixin, AttendanceNavMixin, CreateView):
    model = ShiftAssignment
    form_class = ShiftAssignmentForm
    template_name = 'attendance/shiftassignment_form.html'
    success_url = reverse_lazy('attendance:shiftassignment_list')
    permission_required = ADD_SHIFT

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Shift assignment saved.')
        return super().form_valid(form)
