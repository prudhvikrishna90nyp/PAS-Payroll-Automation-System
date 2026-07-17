from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.clients.models import Client
from apps.company.models import Branch, Company, Department, Designation

from .filters import employee_list_queryset
from .forms import EmployeeDocumentForm, EmployeeForm, EmployeeImportForm
from .import_export import (
    export_employee_template,
    export_employees,
    export_import_errors,
    import_employees,
)
from .models import Employee, EmploymentStatus, EmploymentType
from .pdf_export import render_employee_register_pdf
from .permissions import (
    ADD_EMPLOYEE,
    CHANGE_EMPLOYEE,
    DELETE_EMPLOYEE,
    VIEW_EMPLOYEE,
)


class EmployeeLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Require authentication and an employee model permission."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class EmployeeListView(EmployeeLoginPermissionMixin, ListView):
    model = Employee
    template_name = 'employee/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 10
    permission_required = VIEW_EMPLOYEE

    def get_queryset(self):
        return employee_list_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['branch_filter'] = self.request.GET.get('branch', '')
        context['department_filter'] = self.request.GET.get('department', '')
        context['designation_filter'] = self.request.GET.get('designation', '')
        context['client_filter'] = self.request.GET.get('client', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['employment_status_filter'] = self.request.GET.get('employment_status', '')
        context['employment_type_filter'] = self.request.GET.get('employment_type', '')
        context['pf_eligible_filter'] = self.request.GET.get('pf_eligible', '')
        context['esi_eligible_filter'] = self.request.GET.get('esi_eligible', '')
        context['clients'] = Client.objects.filter(is_active=True).order_by('client_name')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['branches'] = Branch.objects.filter(is_active=True).order_by(
            'company__company_name', 'branch_name'
        )
        context['departments'] = Department.objects.filter(is_active=True).order_by(
            'company__company_name', 'name'
        )
        context['designations'] = Designation.objects.filter(is_active=True).order_by(
            'company__company_name', 'name'
        )
        context['employment_statuses'] = EmploymentStatus.choices
        context['employment_types'] = EmploymentType.choices
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class EmployeeDetailView(EmployeeLoginPermissionMixin, DetailView):
    model = Employee
    template_name = 'employee/employee_detail.html'
    context_object_name = 'employee'
    permission_required = VIEW_EMPLOYEE

    def get_queryset(self):
        return Employee.objects.select_related(
            'company',
            'company__client',
            'branch',
            'department',
            'designation',
            'salary_structure',
            'created_by',
            'updated_by',
        ).prefetch_related('documents')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document_form'] = EmployeeDocumentForm()
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm(CHANGE_EMPLOYEE):
            messages.error(request, 'You do not have permission to upload documents.')
            return redirect('employees:employee_detail', pk=kwargs['pk'])
        self.object = self.get_object()
        form = EmployeeDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.employee = self.object
            document.save()
            messages.success(request, 'Document uploaded successfully.')
        else:
            messages.error(request, 'Could not upload document. Please check the file and try again.')
        return redirect('employees:employee_detail', pk=self.object.pk)


class EmployeeCreateView(EmployeeLoginPermissionMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = ADD_EMPLOYEE

    def get_initial(self):
        initial = super().get_initial()
        for key in ('company', 'branch', 'department', 'designation'):
            value = self.request.GET.get(key)
            if value:
                initial[key] = value
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Employee created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class EmployeeUpdateView(EmployeeLoginPermissionMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = CHANGE_EMPLOYEE

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Employee updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class EmployeeArchiveView(EmployeeLoginPermissionMixin, View):
    permission_required = DELETE_EMPLOYEE

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.is_active = False
        employee.updated_by = request.user
        employee.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{employee.full_name} was archived.')
        return redirect('employees:employee_list')


class EmployeeRestoreView(EmployeeLoginPermissionMixin, View):
    permission_required = CHANGE_EMPLOYEE

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.is_active = True
        employee.updated_by = request.user
        employee.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{employee.full_name} was restored.')
        return redirect('employees:employee_list')


class EmployeeExportView(EmployeeLoginPermissionMixin, View):
    permission_required = VIEW_EMPLOYEE

    def get(self, request):
        if request.GET.get('template') == '1':
            return export_employee_template()
        queryset = employee_list_queryset(request.GET)
        report = request.GET.get('report', '').strip()
        filename = {
            'register': 'employee_register.xlsx',
            'pf': 'pf_employees.xlsx',
            'esi': 'esi_employees.xlsx',
        }.get(report, 'employees_export.xlsx')
        return export_employees(queryset, filename=filename)


class EmployeePdfExportView(EmployeeLoginPermissionMixin, View):
    permission_required = VIEW_EMPLOYEE

    def get(self, request):
        queryset = employee_list_queryset(request.GET)
        report = request.GET.get('report', '').strip()
        title = {
            'register': 'Employee Register',
            'pf': 'PF Eligible Employees',
            'esi': 'ESI Eligible Employees',
        }.get(report, 'Employee Register')
        return render_employee_register_pdf(queryset, title=title, request=request)


class EmployeeImportView(EmployeeLoginPermissionMixin, View):
    template_name = 'employee/employee_import.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = ADD_EMPLOYEE

    def get(self, request):
        return render(request, self.template_name, {'form': EmployeeImportForm()})

    def post(self, request):
        if request.POST.get('download_errors') and request.session.get('employee_import_errors'):
            return export_import_errors(request.session['employee_import_errors'])

        form = EmployeeImportForm(request.POST, request.FILES)
        if form.is_valid():
            created, skipped, errors = import_employees(
                form.cleaned_data['company'],
                form.cleaned_data['file'],
                request.user,
            )
            if created:
                messages.success(request, f'{created} employee(s) imported successfully.')
            if skipped:
                messages.info(request, f'{skipped} duplicate row(s) were skipped.')
            if errors:
                request.session['employee_import_errors'] = errors
                messages.warning(
                    request,
                    f'{len(errors)} row(s) had issues. Download the error log for details.',
                )
            elif created:
                request.session.pop('employee_import_errors', None)
                return redirect(self.success_url)
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'import_errors': errors,
                    'created_count': created,
                    'skipped_count': skipped,
                },
            )
        messages.error(request, 'Please upload a valid Excel file.')
        return render(request, self.template_name, {'form': form})
