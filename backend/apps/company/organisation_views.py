from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.clients.models import Client

from .forms import BranchForm, DepartmentForm, DesignationForm
from .models import Branch, Company, Department, Designation


class OrganisationFilterMixin:
    paginate_by = 10
    search_fields = ()
    name_field = 'name'

    def get_base_queryset(self):
        raise NotImplementedError

    def get_queryset(self):
        queryset = self.get_base_queryset()

        search_query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        company_id = self.request.GET.get('company', '').strip()
        client_id = self.request.GET.get('client', '').strip()

        if search_query:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f'{field}__icontains': search_query})
            queryset = queryset.filter(filters)

        if company_id:
            queryset = queryset.filter(company_id=company_id)

        if client_id:
            queryset = queryset.filter(company__client_id=client_id)

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('company__company_name', self.name_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['company_filter'] = self.request.GET.get('company', '')
        context['client_filter'] = self.request.GET.get('client', '')
        context['clients'] = Client.objects.filter(is_active=True).order_by('client_name')
        context['companies'] = Company.objects.filter(is_active=True).order_by('company_name')
        return context


class OrganisationCreateMixin:
    def get_initial(self):
        initial = super().get_initial()
        company_id = self.request.GET.get('company')
        if company_id:
            initial['company'] = company_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class OrganisationUpdateMixin:
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class BranchListView(OrganisationFilterMixin, LoginRequiredMixin, ListView):
    model = Branch
    template_name = 'organisation/branch_list.html'
    context_object_name = 'branches'
    search_fields = ('branch_name', 'code', 'company__company_name', 'state')
    name_field = 'branch_name'

    def get_base_queryset(self):
        return Branch.objects.select_related('company', 'company__client')


class BranchDetailView(LoginRequiredMixin, DetailView):
    model = Branch
    template_name = 'organisation/branch_detail.html'
    context_object_name = 'branch'

    def get_queryset(self):
        return Branch.objects.select_related('company', 'company__client', 'created_by', 'updated_by')


class BranchCreateView(OrganisationCreateMixin, LoginRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'organisation/branch_form.html'
    success_url = reverse_lazy('organisation:branch_list')
    success_message = 'Branch created successfully.'


class BranchUpdateView(OrganisationUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'organisation/branch_form.html'
    success_url = reverse_lazy('organisation:branch_list')
    success_message = 'Branch updated successfully.'


class BranchArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        branch.is_active = False
        branch.updated_by = request.user
        branch.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{branch.branch_name} was archived.')
        return redirect('organisation:branch_list')


class BranchRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        branch.is_active = True
        branch.updated_by = request.user
        branch.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{branch.branch_name} was restored.')
        return redirect('organisation:branch_list')


class DepartmentListView(OrganisationFilterMixin, LoginRequiredMixin, ListView):
    model = Department
    template_name = 'organisation/department_list.html'
    context_object_name = 'departments'
    search_fields = ('name', 'code', 'company__company_name')
    name_field = 'name'

    def get_base_queryset(self):
        return Department.objects.select_related('company', 'company__client')


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'organisation/department_detail.html'
    context_object_name = 'department'

    def get_queryset(self):
        return Department.objects.select_related('company', 'company__client', 'created_by', 'updated_by')


class DepartmentCreateView(OrganisationCreateMixin, LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'organisation/department_form.html'
    success_url = reverse_lazy('organisation:department_list')
    success_message = 'Department created successfully.'


class DepartmentUpdateView(OrganisationUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'organisation/department_form.html'
    success_url = reverse_lazy('organisation:department_list')
    success_message = 'Department updated successfully.'


class DepartmentArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        department.is_active = False
        department.updated_by = request.user
        department.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{department.name} was archived.')
        return redirect('organisation:department_list')


class DepartmentRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        department.is_active = True
        department.updated_by = request.user
        department.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{department.name} was restored.')
        return redirect('organisation:department_list')


class DesignationListView(OrganisationFilterMixin, LoginRequiredMixin, ListView):
    model = Designation
    template_name = 'organisation/designation_list.html'
    context_object_name = 'designations'
    search_fields = ('name', 'code', 'company__company_name')
    name_field = 'name'

    def get_base_queryset(self):
        return Designation.objects.select_related('company', 'company__client')


class DesignationDetailView(LoginRequiredMixin, DetailView):
    model = Designation
    template_name = 'organisation/designation_detail.html'
    context_object_name = 'designation'

    def get_queryset(self):
        return Designation.objects.select_related('company', 'company__client', 'created_by', 'updated_by')


class DesignationCreateView(OrganisationCreateMixin, LoginRequiredMixin, CreateView):
    model = Designation
    form_class = DesignationForm
    template_name = 'organisation/designation_form.html'
    success_url = reverse_lazy('organisation:designation_list')
    success_message = 'Designation created successfully.'


class DesignationUpdateView(OrganisationUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Designation
    form_class = DesignationForm
    template_name = 'organisation/designation_form.html'
    success_url = reverse_lazy('organisation:designation_list')
    success_message = 'Designation updated successfully.'


class DesignationArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        designation = get_object_or_404(Designation, pk=pk)
        designation.is_active = False
        designation.updated_by = request.user
        designation.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{designation.name} was archived.')
        return redirect('organisation:designation_list')


class DesignationRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        designation = get_object_or_404(Designation, pk=pk)
        designation.is_active = True
        designation.updated_by = request.user
        designation.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{designation.name} was restored.')
        return redirect('organisation:designation_list')
