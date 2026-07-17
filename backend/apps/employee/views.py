from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.clients.models import Client
from apps.company.models import Branch, Company, Department, Designation

from .forms import EmployeeDocumentForm, EmployeeForm, EmployeeImportForm
from .import_export import export_employee_template, export_employees, import_employees
from .models import Employee, EmploymentStatus


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'employee/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 10

    def get_queryset(self):
        queryset = Employee.objects.select_related(
            'company',
            'company__client',
            'branch',
            'department',
            'designation',
        )

        search_query = self.request.GET.get('q', '').strip()
        company_id = self.request.GET.get('company', '').strip()
        branch_id = self.request.GET.get('branch', '').strip()
        department_id = self.request.GET.get('department', '').strip()
        designation_id = self.request.GET.get('designation', '').strip()
        client_id = self.request.GET.get('client', '').strip()
        status = self.request.GET.get('status', '').strip()
        employment_status = self.request.GET.get('employment_status', '').strip()
        pf_eligible = self.request.GET.get('pf_eligible', '').strip()
        esi_eligible = self.request.GET.get('esi_eligible', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(employee_code__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(mobile__icontains=search_query)
                | Q(pan__icontains=search_query)
                | Q(aadhaar__icontains=search_query)
                | Q(company__company_name__icontains=search_query)
            )

        if client_id:
            queryset = queryset.filter(company__client_id=client_id)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if designation_id:
            queryset = queryset.filter(designation_id=designation_id)
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        if employment_status:
            queryset = queryset.filter(employment_status=employment_status)
        if pf_eligible == 'yes':
            queryset = queryset.filter(pf_eligible=True)
        elif pf_eligible == 'no':
            queryset = queryset.filter(pf_eligible=False)
        if esi_eligible == 'yes':
            queryset = queryset.filter(esi_eligible=True)
        elif esi_eligible == 'no':
            queryset = queryset.filter(esi_eligible=False)

        return queryset.order_by('company__company_name', 'employee_code')

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
        context['pf_eligible_filter'] = self.request.GET.get('pf_eligible', '')
        context['esi_eligible_filter'] = self.request.GET.get('esi_eligible', '')
        context['clients'] = Client.objects.filter(is_active=True).order_by('client_name')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        context['branches'] = Branch.objects.filter(is_active=True).order_by('company__company_name', 'branch_name')
        context['departments'] = Department.objects.filter(is_active=True).order_by('company__company_name', 'name')
        context['designations'] = Designation.objects.filter(is_active=True).order_by('company__company_name', 'name')
        context['employment_statuses'] = EmploymentStatus.choices
        return context


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employee/employee_detail.html'
    context_object_name = 'employee'

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


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employees:employee_list')

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


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employees:employee_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Employee updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class EmployeeArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.is_active = False
        employee.updated_by = request.user
        employee.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{employee.full_name} was archived.')
        return redirect('employees:employee_list')


class EmployeeRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.is_active = True
        employee.updated_by = request.user
        employee.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{employee.full_name} was restored.')
        return redirect('employees:employee_list')


class EmployeeExportView(LoginRequiredMixin, View):
    def get(self, request):
        queryset = Employee.objects.select_related('branch', 'department', 'designation')
        company_id = request.GET.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if request.GET.get('template') == '1':
            return export_employee_template()
        return export_employees(queryset)


class EmployeeImportView(LoginRequiredMixin, View):
    template_name = 'employee/employee_import.html'
    success_url = reverse_lazy('employees:employee_list')

    def get(self, request):
        from django.shortcuts import render

        return render(request, self.template_name, {'form': EmployeeImportForm()})

    def post(self, request):
        from django.shortcuts import render

        form = EmployeeImportForm(request.POST, request.FILES)
        if form.is_valid():
            created, errors = import_employees(
                form.cleaned_data['company'],
                form.cleaned_data['file'],
                request.user,
            )
            if created:
                messages.success(request, f'{created} employee(s) imported successfully.')
            if errors:
                messages.warning(request, 'Some rows could not be imported: ' + '; '.join(errors[:5]))
            if created and not errors:
                return redirect(self.success_url)
        else:
            messages.error(request, 'Please upload a valid Excel file.')
        return render(request, self.template_name, {'form': form})
