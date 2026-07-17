from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from openpyxl import Workbook

from apps.company.models import Branch, Company, Department
from apps.employee.models import Employee

from .filters import assignment_list_queryset, component_list_queryset, structure_list_queryset
from .forms import (
    EmployeeSalaryAssignmentForm,
    PayrollPeriodForm,
    PayrollRunForm,
    SalaryComponentForm,
    SalaryStructureForm,
    SalaryStructureLineFormSet,
    SeedComponentsForm,
)
from .models import (
    CalculationType,
    ComponentType,
    EmployeeSalaryAssignment,
    PayPeriod,
    PayrollAuditLog,
    PayrollPeriod,
    PayrollPeriodStatus,
    PayrollResult,
    PayrollRun,
    PayrollRunStatus,
    Payslip,
    SalaryComponent,
    SalaryStructure,
)
from .permissions import (
    ADD_ASSIGNMENT,
    ADD_COMPONENT,
    ADD_PERIOD,
    ADD_RUN,
    ADD_STRUCTURE,
    CHANGE_ASSIGNMENT,
    CHANGE_COMPONENT,
    CHANGE_PERIOD,
    CHANGE_RUN,
    CHANGE_STRUCTURE,
    DELETE_ASSIGNMENT,
    DELETE_COMPONENT,
    DELETE_STRUCTURE,
    EXPORT_ASSIGNMENT,
    EXPORT_COMPONENT,
    EXPORT_STRUCTURE,
    VIEW_ASSIGNMENT,
    VIEW_COMPONENT,
    VIEW_PAYSLIP,
    VIEW_PERIOD,
    VIEW_RUN,
    VIEW_STRUCTURE,
)
from .reports import REPORT_BUILDERS
from .services import generate_payslips_for_period
from .services.approval import approve_run, mark_reviewed
from .services.exceptions import (
    InvalidTransitionError,
    LockedRunError,
    PayrollCalculationError,
    PayrollWorkflowError,
    RunNotCalculableError,
    RunNotReadyError,
)
from .services.locking import lock_run
from .services.payroll_engine import calculate_run, close_period, create_run, open_period
from .services.export_service import ENGINE_EXPORT_BUILDERS
from .services.payslip_data import build_payslip_dataset
from .services.report_queries import (
    ReportFilters,
    aggregate_component_totals,
    aggregate_result_totals,
    branch_summary,
    company_summary,
    component_queryset,
    companies_visible_to_user,
    department_summary,
    load_employees_map,
    results_queryset,
    run_control_queryset,
    status_label_for_display,
)
from .services import permissions as workflow_perms
from .services.salary_calculator import calculate_assignment_components, calculate_structure_components
from .services.validation import validate_structure


class PayrollLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class PayrollNavMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payroll_nav'] = True
        return context


# ---- Payslips (legacy function views) ----

def payslip_list(request):
    pay_periods = PayPeriod.objects.all()
    selected_period_id = request.GET.get('period')
    payslips = Payslip.objects.select_related('employee', 'pay_period')

    if selected_period_id:
        payslips = payslips.filter(pay_period_id=selected_period_id)

    return render(
        request,
        'payroll/payslip_list.html',
        {
            'payslips': payslips,
            'pay_periods': pay_periods,
            'selected_period_id': int(selected_period_id) if selected_period_id else None,
            'payroll_nav': True,
        },
    )


def payslip_detail(request, pk):
    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'pay_period').prefetch_related('items'),
        pk=pk,
    )
    earnings = payslip.items.filter(item_type='earning')
    deductions = payslip.items.filter(item_type='deduction')
    return render(
        request,
        'payroll/payslip_detail.html',
        {
            'payslip': payslip,
            'earnings': earnings,
            'deductions': deductions,
            'payroll_nav': True,
        },
    )


def payslip_pdf(request, pk):
    try:
        from weasyprint import HTML
    except OSError:
        return HttpResponse(
            'PDF generation requires WeasyPrint system libraries. '
            'On Windows, install GTK3 runtime: '
            'https://doc.courtbouillon.org/weasyprint/stable/first_steps.html',
            status=503,
        )

    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'pay_period').prefetch_related('items'),
        pk=pk,
    )
    html = render_to_string(
        'payroll/payslip_pdf.html',
        {
            'payslip': payslip,
            'earnings': payslip.items.filter(item_type='earning'),
            'deductions': payslip.items.filter(item_type='deduction'),
        },
    )
    pdf = HTML(string=html).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'payslip_{payslip.employee.employee_id}_{payslip.pay_period}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def payslip_export_excel(request):
    period_id = request.GET.get('period')
    payslips = Payslip.objects.select_related('employee', 'pay_period')
    if period_id:
        payslips = payslips.filter(pay_period_id=period_id)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Payslips'
    sheet.append([
        'Employee ID',
        'Employee Name',
        'Pay Period',
        'Basic Salary',
        'Gross Pay',
        'Deductions',
        'Net Pay',
        'Status',
    ])
    for payslip in payslips:
        sheet.append([
            payslip.employee.employee_id,
            payslip.employee.full_name,
            str(payslip.pay_period),
            float(payslip.basic_salary),
            float(payslip.gross_pay),
            float(payslip.total_deductions),
            float(payslip.net_pay),
            payslip.get_status_display(),
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="payslips.xlsx"'
    return response


@require_POST
def generate_period_payslips(request, period_id):
    pay_period = get_object_or_404(PayPeriod, pk=period_id)
    generate_payslips_for_period(pay_period)
    return redirect(request.META.get('HTTP_REFERER', '/payroll/payslips/'))


# ---- Salary Components ----

class ComponentListView(PayrollLoginPermissionMixin, PayrollNavMixin, ListView):
    model = SalaryComponent
    template_name = 'payroll/component_list.html'
    context_object_name = 'components'
    paginate_by = 20
    permission_required = VIEW_COMPONENT

    def get_queryset(self):
        return component_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['component_type_filter'] = self.request.GET.get('component_type', '')
        context['calculation_type_filter'] = self.request.GET.get('calculation_type', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['component_types'] = ComponentType.choices
        context['calculation_types'] = CalculationType.choices
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class ComponentDetailView(PayrollLoginPermissionMixin, PayrollNavMixin, DetailView):
    model = SalaryComponent
    template_name = 'payroll/component_detail.html'
    context_object_name = 'component'
    permission_required = VIEW_COMPONENT


class ComponentCreateView(PayrollLoginPermissionMixin, PayrollNavMixin, CreateView):
    model = SalaryComponent
    form_class = SalaryComponentForm
    template_name = 'payroll/component_form.html'
    success_url = reverse_lazy('payroll:component_list')
    permission_required = ADD_COMPONENT

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Salary component created.')
        return super().form_valid(form)


class ComponentUpdateView(PayrollLoginPermissionMixin, PayrollNavMixin, UpdateView):
    model = SalaryComponent
    form_class = SalaryComponentForm
    template_name = 'payroll/component_form.html'
    success_url = reverse_lazy('payroll:component_list')
    permission_required = CHANGE_COMPONENT

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Salary component updated.')
        return super().form_valid(form)


class ComponentArchiveView(PayrollLoginPermissionMixin, View):
    permission_required = DELETE_COMPONENT

    def post(self, request, pk):
        component = get_object_or_404(SalaryComponent, pk=pk)
        component.soft_delete()
        messages.success(request, f'Component {component.component_code} archived.')
        return redirect('payroll:component_list')


class SeedComponentsView(PayrollLoginPermissionMixin, PayrollNavMixin, View):
    permission_required = ADD_COMPONENT
    template_name = 'payroll/seed_components.html'

    def get(self, request):
        return render(request, self.template_name, {'form': SeedComponentsForm(), 'payroll_nav': True})

    def post(self, request):
        form = SeedComponentsForm(request.POST)
        if form.is_valid():
            created = form.save(user=request.user)
            messages.success(
                request,
                f'Seeded {len(created)} standard component(s) for {form.cleaned_data["company"]}.'
                if created else
                f'All standard components already exist for {form.cleaned_data["company"]}.',
            )
            return redirect('payroll:component_list')
        return render(request, self.template_name, {'form': form, 'payroll_nav': True})


# ---- Salary Structures ----

class StructureListView(PayrollLoginPermissionMixin, PayrollNavMixin, ListView):
    model = SalaryStructure
    template_name = 'payroll/structure_list.html'
    context_object_name = 'structures'
    paginate_by = 20
    permission_required = VIEW_STRUCTURE

    def get_queryset(self):
        return structure_list_queryset(self.request.GET)

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


class StructureDetailView(PayrollLoginPermissionMixin, PayrollNavMixin, DetailView):
    model = SalaryStructure
    template_name = 'payroll/structure_detail.html'
    context_object_name = 'structure'
    permission_required = VIEW_STRUCTURE

    def get_queryset(self):
        return SalaryStructure.objects.select_related('company').prefetch_related(
            'lines__component'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['validation_errors'] = validate_structure(self.object)
        gross = self.request.GET.get('gross') or '50000'
        try:
            gross_dec = Decimal(gross)
            context['preview'] = calculate_structure_components(self.object, gross_dec)
            context['preview_gross'] = gross_dec
        except Exception as exc:
            context['preview_error'] = str(exc)
            context['preview_gross'] = gross
        return context


class StructureCreateView(PayrollLoginPermissionMixin, PayrollNavMixin, CreateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'payroll/structure_form.html'
    permission_required = ADD_STRUCTURE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = None
        company_id = self.request.POST.get('company') or self.request.GET.get('company')
        if company_id:
            company = Company.objects.filter(pk=company_id).first()
        instance = getattr(self, 'object', None)
        if self.request.method == 'POST':
            context['line_formset'] = SalaryStructureLineFormSet(
                self.request.POST, instance=instance, form_kwargs={'company': company}
            )
        else:
            context['line_formset'] = SalaryStructureLineFormSet(
                instance=instance, form_kwargs={'company': company}
            )
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        self.object = form.save()
        formset = SalaryStructureLineFormSet(
            self.request.POST,
            instance=self.object,
            form_kwargs={'company': self.object.company},
        )
        if formset.is_valid():
            formset.save()
            messages.success(self.request, 'Salary structure created.')
            return redirect(self.object.get_absolute_url())
        messages.error(self.request, 'Please correct the structure line errors.')
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return self.render_to_response(self.get_context_data(form=form))


class StructureUpdateView(PayrollLoginPermissionMixin, PayrollNavMixin, UpdateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'payroll/structure_form.html'
    permission_required = CHANGE_STRUCTURE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.object.company if self.object else None
        if self.request.method == 'POST':
            context['line_formset'] = SalaryStructureLineFormSet(
                self.request.POST, instance=self.object, form_kwargs={'company': company}
            )
        else:
            context['line_formset'] = SalaryStructureLineFormSet(
                instance=self.object, form_kwargs={'company': company}
            )
        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        self.object = form.save()
        formset = SalaryStructureLineFormSet(
            self.request.POST,
            instance=self.object,
            form_kwargs={'company': self.object.company},
        )
        if formset.is_valid():
            formset.save()
            messages.success(self.request, 'Salary structure updated.')
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return self.render_to_response(self.get_context_data(form=form))


class StructureArchiveView(PayrollLoginPermissionMixin, View):
    permission_required = DELETE_STRUCTURE

    def post(self, request, pk):
        structure = get_object_or_404(SalaryStructure, pk=pk)
        structure.soft_delete()
        messages.success(request, f'Structure {structure.code} archived.')
        return redirect('payroll:structure_list')


# ---- Employee Salary Assignments ----

class AssignmentListView(PayrollLoginPermissionMixin, PayrollNavMixin, ListView):
    model = EmployeeSalaryAssignment
    template_name = 'payroll/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    permission_required = VIEW_ASSIGNMENT

    def get_queryset(self):
        return assignment_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['structure_filter'] = self.request.GET.get('structure', '')
        context['current_filter'] = self.request.GET.get('current', '')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['structures'] = SalaryStructure.objects.filter(is_active=True).order_by('name')
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class AssignmentDetailView(PayrollLoginPermissionMixin, PayrollNavMixin, DetailView):
    model = EmployeeSalaryAssignment
    template_name = 'payroll/assignment_detail.html'
    context_object_name = 'assignment'
    permission_required = VIEW_ASSIGNMENT

    def get_queryset(self):
        return EmployeeSalaryAssignment.objects.select_related(
            'employee', 'employee__company', 'salary_structure'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['breakdown'] = calculate_assignment_components(self.object)
        except Exception as exc:
            context['breakdown_error'] = str(exc)
        return context


class AssignmentCreateView(PayrollLoginPermissionMixin, PayrollNavMixin, CreateView):
    model = EmployeeSalaryAssignment
    form_class = EmployeeSalaryAssignmentForm
    template_name = 'payroll/assignment_form.html'
    success_url = reverse_lazy('payroll:assignment_list')
    permission_required = ADD_ASSIGNMENT

    def get_initial(self):
        initial = super().get_initial()
        emp = self.request.GET.get('employee')
        if emp:
            initial['employee'] = emp
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        if not form.instance.ctc:
            try:
                result = calculate_structure_components(
                    form.instance.salary_structure,
                    form.instance.gross_salary,
                )
                form.instance.ctc = (result.ctc_monthly * 12).quantize(Decimal('0.01'))
            except Exception:
                form.instance.ctc = form.instance.gross_salary * 12
        messages.success(self.request, 'Employee salary assignment created.')
        return super().form_valid(form)


class AssignmentUpdateView(PayrollLoginPermissionMixin, PayrollNavMixin, UpdateView):
    model = EmployeeSalaryAssignment
    form_class = EmployeeSalaryAssignmentForm
    template_name = 'payroll/assignment_form.html'
    success_url = reverse_lazy('payroll:assignment_list')
    permission_required = CHANGE_ASSIGNMENT

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Employee salary assignment updated.')
        return super().form_valid(form)


class AssignmentArchiveView(PayrollLoginPermissionMixin, View):
    permission_required = DELETE_ASSIGNMENT

    def post(self, request, pk):
        assignment = get_object_or_404(EmployeeSalaryAssignment, pk=pk)
        assignment.soft_delete()
        messages.success(request, 'Salary assignment archived.')
        return redirect('payroll:assignment_list')


# ---- Reports ----

ENGINE_REPORT_SLUGS = {
    'payroll-register': 'payroll_register',
    'earnings-register': 'earnings_register',
    'deductions-register': 'deductions_register',
    'net-salary-register': 'net_salary_register',
    'employee-payroll-detail': 'employee_payroll_detail',
    'department-payroll-summary': 'department_payroll_summary',
    'branch-payroll-summary': 'branch_payroll_summary',
    'company-payroll-summary': 'company_payroll_summary',
    'payroll-run-control': 'payroll_run_control',
}
ENGINE_REPORTS = [
    ('payroll-register', 'Payroll Register', 'Payroll result snapshots by employee.'),
    ('earnings-register', 'Earnings Register', 'Earning component amounts by employee.'),
    ('deductions-register', 'Deductions Register', 'Deduction component amounts by employee.'),
    ('net-salary-register', 'Net Salary Register', 'Gross, deductions, and net salary by employee.'),
    ('employee-payroll-detail', 'Employee Payroll Detail', 'Attendance and full payroll snapshot per employee.'),
    ('department-payroll-summary', 'Department Payroll Summary', 'Payroll totals grouped by department.'),
    ('branch-payroll-summary', 'Branch Payroll Summary', 'Payroll totals grouped by branch.'),
    ('company-payroll-summary', 'Company Payroll Summary', 'Payroll totals grouped by company.'),
    ('payroll-run-control', 'Payroll Run Control', 'Control totals and statuses by payroll run.'),
]


def _engine_report_data(report_key, filters):
    """Return display columns, snapshot-derived rows, and unpaginated totals."""
    result_columns = [
        'Company', 'Period', 'Run #', 'Status', 'Employee code', 'Employee name',
    ]
    if report_key in {'payroll_register', 'net_salary_register', 'employee_payroll_detail'}:
        results = list(results_queryset(filters))
        employees = load_employees_map({result.employee_id for result in results})
        rows = []
        for result in results:
            run, employee = result.run, employees.get(result.employee_id)
            base = [
                run.company.company_name, f'{run.period.month:02d}/{run.period.year}',
                run.run_number, status_label_for_display(run.status),
                getattr(employee, 'employee_code', ''), getattr(employee, 'full_name', ''),
            ]
            if report_key == 'payroll_register':
                rows.append({'cells': base + [
                    getattr(getattr(employee, 'branch', None), 'branch_name', ''),
                    getattr(getattr(employee, 'department', None), 'name', ''),
                    result.present_days, result.lop_days, result.gross, result.total_earnings,
                    result.total_deductions, result.net_salary,
                ]})
            elif report_key == 'net_salary_register':
                rows.append({'cells': base + [result.gross, result.total_deductions, result.net_salary]})
            else:
                rows.append({'cells': base + [
                    result.present_days, result.absent_days, result.lop_days, result.overtime_hours,
                    result.gross, result.total_earnings, result.total_deductions,
                    result.net_salary, result.ctc_snapshot,
                ]})
        columns = {
            'payroll_register': result_columns + ['Branch', 'Department', 'Present', 'LOP', 'Gross', 'Earnings', 'Deductions', 'Net'],
            'net_salary_register': result_columns + ['Gross', 'Deductions', 'Net'],
            'employee_payroll_detail': result_columns + ['Present', 'Absent', 'LOP', 'Overtime', 'Gross', 'Earnings', 'Deductions', 'Net', 'CTC'],
        }[report_key]
        return columns, rows, aggregate_result_totals(results_queryset(filters))

    if report_key in {'earnings_register', 'deductions_register'}:
        component_type = ComponentType.EARNING if report_key == 'earnings_register' else ComponentType.DEDUCTION
        components = list(component_queryset(filters, component_type))
        employees = load_employees_map({item.result.employee_id for item in components})
        rows = [
            {'cells': [
                item.result.run.company.company_name,
                f'{item.result.run.period.month:02d}/{item.result.run.period.year}',
                item.result.run.run_number, status_label_for_display(item.result.run.status),
                getattr(employees.get(item.result.employee_id), 'employee_code', ''),
                getattr(employees.get(item.result.employee_id), 'full_name', ''),
                item.component_code, item.component_name, item.amount,
            ]}
            for item in components
        ]
        return result_columns + ['Component code', 'Component name', 'Amount'], rows, aggregate_component_totals(component_queryset(filters, component_type))

    if report_key in {'department_payroll_summary', 'branch_payroll_summary', 'company_payroll_summary'}:
        summary = {
            'department_payroll_summary': department_summary,
            'branch_payroll_summary': branch_summary,
            'company_payroll_summary': company_summary,
        }[report_key]
        summary_rows, totals = summary(filters)
        rows = [{'cells': [row.name, row.employee_count, row.gross, row.total_earnings, row.total_deductions, row.net_salary]} for row in summary_rows]
        label = {
            'department_payroll_summary': 'Department',
            'branch_payroll_summary': 'Branch',
            'company_payroll_summary': 'Company',
        }[report_key]
        return [label, 'Employees', 'Gross', 'Earnings', 'Deductions', 'Net'], rows, totals

    if report_key == 'payroll_run_control':
        rows = []
        for run in run_control_queryset(filters).prefetch_related('results'):
            totals = aggregate_result_totals(run.results.all())
            rows.append({'cells': [
                run.company.company_name, f'{run.period.month:02d}/{run.period.year}',
                run.run_number, status_label_for_display(run.status), run.results.count(),
                totals['gross'], totals['total_earnings'], totals['total_deductions'], totals['net_salary'],
            ]})
        return ['Company', 'Period', 'Run #', 'Status', 'Results', 'Gross', 'Earnings', 'Deductions', 'Net'], rows, aggregate_result_totals(results_queryset(filters))

    raise Http404('Unknown engine report.')


class PayrollReportIndexView(PayrollLoginPermissionMixin, PayrollNavMixin, View):
    permission_required = VIEW_STRUCTURE
    template_name = 'payroll/report_index.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                'payroll_nav': True,
                'companies': Company.objects.filter(is_active=True).order_by('company_name'),
                'reports': [
                    ('component_register', 'Component Register'),
                    ('structure_register', 'Structure Register'),
                    ('employee_salary_register', 'Employee Salary Register'),
                    ('salary_revision', 'Salary Revision Report'),
                    ('ctc_register', 'CTC Register'),
                ],
                'engine_reports': ENGINE_REPORTS,
            },
        )


class EngineReportPageView(PayrollLoginPermissionMixin, PayrollNavMixin, View):
    permission_required = VIEW_RUN
    template_name = 'payroll/engine_report.html'

    def get(self, request, report_slug):
        report_key = ENGINE_REPORT_SLUGS.get(report_slug)
        if not report_key:
            raise Http404('Unknown engine report.')
        filters = ReportFilters.from_params(request.GET, user=request.user)
        columns, rows, totals = _engine_report_data(report_key, filters)
        if report_key not in {
            'department_payroll_summary', 'branch_payroll_summary', 'company_payroll_summary',
        }:
            for row in rows:
                row['status'] = row['cells'][3]
        query = request.GET.copy()
        query.pop('page', None)
        visible_company_ids = companies_visible_to_user(request.user)
        companies = Company.objects.filter(is_active=True).order_by('company_name')
        if visible_company_ids is not None:
            companies = companies.filter(pk__in=visible_company_ids)
        title, description = next((title, description) for slug, title, description in ENGINE_REPORTS if slug == report_slug)
        return render(request, self.template_name, {
            'payroll_nav': True,
            'report_slug': report_slug,
            'report_title': title,
            'report_description': description,
            'columns': columns,
            'page_obj': Paginator(rows, 25).get_page(request.GET.get('page')),
            'totals': totals,
            'companies': companies,
            'periods': PayrollPeriod.objects.select_related('company').order_by('-year', '-month')[:100],
            'branches': Branch.objects.order_by('company__company_name', 'branch_name'),
            'departments': Department.objects.order_by('company__company_name', 'name'),
            'filters': filters,
            'export_query': query.urlencode(),
        })


class EngineReportExportView(PayrollLoginPermissionMixin, View):
    permission_required = VIEW_RUN

    def get(self, request, report_slug):
        report_key = ENGINE_REPORT_SLUGS.get(report_slug)
        builder = ENGINE_EXPORT_BUILDERS.get(report_key)
        if not builder:
            raise Http404('Unknown engine report.')
        return builder(ReportFilters.from_params(request.GET, user=request.user))


class PayslipPreviewView(PayrollLoginPermissionMixin, PayrollNavMixin, View):
    permission_required = VIEW_RUN
    template_name = 'payroll/payslip_preview.html'

    def get(self, request, run_id, result_id):
        result = get_object_or_404(
            PayrollResult.objects.select_related('run', 'run__company', 'run__period').prefetch_related('components'),
            pk=result_id,
            run_id=run_id,
        )
        return render(request, self.template_name, {
            'payroll_nav': True,
            'dataset': build_payslip_dataset(result),
        })


class PayrollReportDownloadView(PayrollLoginPermissionMixin, View):
    permission_required = VIEW_STRUCTURE

    def get(self, request, report_type):
        builder = REPORT_BUILDERS.get(report_type)
        if not builder:
            messages.error(request, 'Unknown report type.')
            return redirect('payroll:report_index')
        perm_map = {
            'component_register': EXPORT_COMPONENT,
            'structure_register': EXPORT_STRUCTURE,
            'employee_salary_register': EXPORT_ASSIGNMENT,
            'salary_revision': EXPORT_ASSIGNMENT,
            'ctc_register': EXPORT_ASSIGNMENT,
        }
        needed = perm_map.get(report_type)
        if needed and not request.user.has_perm(needed) and not request.user.has_perm(VIEW_STRUCTURE):
            raise PermissionDenied
        return builder(request.GET)


# ---- Payroll Periods (Sprint 8.1) ----

class PeriodListView(PayrollLoginPermissionMixin, PayrollNavMixin, ListView):
    model = PayrollPeriod
    template_name = 'payroll/period_list.html'
    context_object_name = 'periods'
    paginate_by = 20
    permission_required = VIEW_PERIOD

    def get_queryset(self):
        qs = PayrollPeriod.objects.select_related('company')
        company = self.request.GET.get('company')
        status = self.request.GET.get('status')
        if company:
            qs = qs.filter(company_id=company)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['company_filter'] = self.request.GET.get('company', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['status_choices'] = PayrollPeriodStatus.choices
        return context


class PeriodDetailView(PayrollLoginPermissionMixin, PayrollNavMixin, DetailView):
    model = PayrollPeriod
    template_name = 'payroll/period_detail.html'
    context_object_name = 'period'
    permission_required = VIEW_PERIOD

    def get_queryset(self):
        return PayrollPeriod.objects.select_related('company').prefetch_related('runs')


class PeriodCreateView(PayrollLoginPermissionMixin, PayrollNavMixin, CreateView):
    model = PayrollPeriod
    form_class = PayrollPeriodForm
    template_name = 'payroll/period_form.html'
    success_url = reverse_lazy('payroll:period_list')
    permission_required = ADD_PERIOD

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Payroll period created.')
        return super().form_valid(form)


class PeriodCloseView(PayrollLoginPermissionMixin, View):
    permission_required = CHANGE_PERIOD

    def post(self, request, pk):
        period = get_object_or_404(PayrollPeriod, pk=pk)
        try:
            close_period(period, user=request.user)
            messages.success(request, f'Period {period} closed.')
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect('payroll:period_detail', pk=pk)


class PeriodOpenView(PayrollLoginPermissionMixin, View):
    permission_required = CHANGE_PERIOD

    def post(self, request, pk):
        period = get_object_or_404(PayrollPeriod, pk=pk)
        open_period(period, user=request.user)
        messages.success(request, f'Period {period} opened.')
        return redirect('payroll:period_detail', pk=pk)


# ---- Payroll Runs (Sprint 8.1) ----

class RunListView(PayrollLoginPermissionMixin, PayrollNavMixin, ListView):
    model = PayrollRun
    template_name = 'payroll/run_list.html'
    context_object_name = 'runs'
    paginate_by = 20
    permission_required = VIEW_RUN

    def get_queryset(self):
        qs = PayrollRun.objects.select_related('company', 'period', 'created_by')
        company = self.request.GET.get('company')
        period = self.request.GET.get('period')
        if company:
            qs = qs.filter(company_id=company)
        if period:
            qs = qs.filter(period_id=period)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['periods'] = PayrollPeriod.objects.select_related('company').order_by(
            '-year', '-month'
        )[:50]
        context['company_filter'] = self.request.GET.get('company', '')
        context['period_filter'] = self.request.GET.get('period', '')
        return context


class RunDetailView(PayrollLoginPermissionMixin, PayrollNavMixin, DetailView):
    model = PayrollRun
    template_name = 'payroll/run_detail.html'
    context_object_name = 'run'
    permission_required = VIEW_RUN

    def get_queryset(self):
        return PayrollRun.objects.select_related('company', 'period', 'created_by')

    def get_context_data(self, **kwargs):
        from django.db.models import Sum

        context = super().get_context_data(**kwargs)
        results_queryset = (
            PayrollResult.objects
            .filter(run=self.object)
            .prefetch_related('components')
            .order_by('employee_id')
        )
        totals = results_queryset.aggregate(
            gross=Sum('gross'),
            total_earnings=Sum('total_earnings'),
            total_deductions=Sum('total_deductions'),
            net_salary=Sum('net_salary'),
        )
        results = list(results_queryset)
        employees = load_employees_map(result.employee_id for result in results)
        for result in results:
            result.employee_display = employees.get(result.employee_id)
        context['results'] = results
        context['totals'] = {
            'gross': totals['gross'] or Decimal('0.00'),
            'total_earnings': totals['total_earnings'] or Decimal('0.00'),
            'total_deductions': totals['total_deductions'] or Decimal('0.00'),
            'net_salary': totals['net_salary'] or Decimal('0.00'),
            'employee_count': len(results),
        }
        user = self.request.user
        run = self.object
        context['can_calculate'] = run.is_calculable and user.has_perm(CHANGE_RUN)
        context['can_review'] = (
            run.status == PayrollRunStatus.CALCULATED
            and not run.calculation_errors
            and workflow_perms.can_review_run(user)
        )
        context['can_approve'] = (
            run.status == PayrollRunStatus.REVIEWED
            and not run.calculation_errors
            and workflow_perms.can_approve_run(user)
        )
        context['can_lock'] = (
            run.status == PayrollRunStatus.APPROVED
            and workflow_perms.can_lock_run(user)
        )
        context['calculation_errors'] = run.calculation_errors or []
        context['PayrollRunStatus'] = PayrollRunStatus
        context['audit_logs'] = (
            PayrollAuditLog.objects
            .filter(run=run)
            .select_related('user')
            .order_by('-timestamp')[:50]
        )
        return context


class RunCalculateView(PayrollLoginPermissionMixin, View):
    permission_required = CHANGE_RUN

    def post(self, request, pk):
        run = get_object_or_404(PayrollRun.objects.select_related('period', 'company'), pk=pk)
        try:
            calculate_run(run, user=request.user)
            run.refresh_from_db()
            if run.status == PayrollRunStatus.INCOMPLETE:
                messages.warning(
                    request,
                    f'Calculation incomplete for run #{run.run_number}: '
                    f'{len(run.calculation_errors)} employee error(s). '
                    'Failed employees have no salary result (not zeroed).',
                )
            else:
                messages.success(
                    request,
                    f'Payroll run #{run.run_number} calculated successfully.',
                )
        except (LockedRunError, RunNotCalculableError, PayrollCalculationError) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'Calculation failed: {exc}')
        return redirect('payroll:run_detail', pk=pk)


class _RunTransitionView(PayrollLoginPermissionMixin, View):
    """Shared POST handler for review / approve / lock."""

    permission_required = VIEW_RUN
    success_message = ''

    def transition(self, run, user, remarks: str):
        raise NotImplementedError

    def post(self, request, pk):
        run = get_object_or_404(PayrollRun.objects.select_related('period', 'company'), pk=pk)
        remarks = (request.POST.get('remarks') or '').strip()
        try:
            self.transition(run, request.user, remarks)
            messages.success(request, self.success_message.format(run=run))
        except PermissionDenied:
            raise
        except (InvalidTransitionError, RunNotReadyError, PayrollWorkflowError) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'Workflow action failed: {exc}')
        return redirect('payroll:run_detail', pk=pk)


class RunReviewView(_RunTransitionView):
    success_message = 'Payroll run #{run.run_number} marked as Reviewed.'

    def transition(self, run, user, remarks: str):
        return mark_reviewed(run, user=user, remarks=remarks)


class RunApproveView(_RunTransitionView):
    success_message = 'Payroll run #{run.run_number} approved.'

    def transition(self, run, user, remarks: str):
        return approve_run(run, user=user, remarks=remarks)


class RunLockView(_RunTransitionView):
    success_message = 'Payroll run #{run.run_number} locked.'

    def transition(self, run, user, remarks: str):
        return lock_run(run, user=user, remarks=remarks)


class RunCreateView(PayrollLoginPermissionMixin, PayrollNavMixin, CreateView):
    model = PayrollRun
    form_class = PayrollRunForm
    template_name = 'payroll/run_form.html'
    permission_required = ADD_RUN

    def form_valid(self, form):
        period = form.cleaned_data['period']
        notes = form.cleaned_data.get('notes') or ''
        try:
            run = create_run(period=period, user=self.request.user, notes=notes)
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Draft payroll run #{run.run_number} created.')
        return redirect('payroll:run_detail', pk=run.pk)

    def get_initial(self):
        initial = super().get_initial()
        period_id = self.request.GET.get('period')
        if period_id:
            initial['period'] = period_id
        return initial
