from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from openpyxl import Workbook

from apps.company.models import Company
from apps.employee.models import Employee

from .filters import assignment_list_queryset, component_list_queryset, structure_list_queryset
from .forms import (
    EmployeeSalaryAssignmentForm,
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
    Payslip,
    SalaryComponent,
    SalaryStructure,
)
from .permissions import (
    ADD_ASSIGNMENT,
    ADD_COMPONENT,
    ADD_STRUCTURE,
    CHANGE_ASSIGNMENT,
    CHANGE_COMPONENT,
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
    VIEW_STRUCTURE,
)
from .reports import REPORT_BUILDERS
from .services import generate_payslips_for_period
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
            },
        )


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
