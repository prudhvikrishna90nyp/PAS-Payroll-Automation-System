from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.clients.models import Client

from .forms import CompanyForm
from .models import Company
from .permissions import ADD_COMPANY, CHANGE_COMPANY, DELETE_COMPANY, VIEW_COMPANY


class CompanyLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class CompanyListView(CompanyLoginPermissionMixin, ListView):
    model = Company
    template_name = 'company/company_list.html'
    context_object_name = 'companies'
    paginate_by = 10
    permission_required = VIEW_COMPANY

    def get_queryset(self):
        queryset = Company.objects.select_related('client')

        search_query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        client_id = self.request.GET.get('client', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(company_name__icontains=search_query)
                | Q(trade_name__icontains=search_query)
                | Q(pan__icontains=search_query)
                | Q(gstin__icontains=search_query)
                | Q(tan__icontains=search_query)
                | Q(client__client_name__icontains=search_query)
            )

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('company_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['client_filter'] = self.request.GET.get('client', '')
        context['clients'] = Client.objects.filter(is_active=True).order_by('client_name')
        return context


class CompanyDetailView(CompanyLoginPermissionMixin, DetailView):
    model = Company
    template_name = 'company/company_detail.html'
    context_object_name = 'company'
    permission_required = VIEW_COMPANY

    def get_queryset(self):
        return Company.objects.select_related('client', 'created_by', 'updated_by')


class CompanyCreateView(CompanyLoginPermissionMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'company/company_form.html'
    success_url = reverse_lazy('company:company_list')
    permission_required = ADD_COMPANY

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get('client')
        if client_id:
            initial['client'] = client_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Company created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class CompanyUpdateView(CompanyLoginPermissionMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'company/company_form.html'
    success_url = reverse_lazy('company:company_list')
    permission_required = CHANGE_COMPANY

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Company updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class CompanyArchiveView(CompanyLoginPermissionMixin, View):
    permission_required = DELETE_COMPANY

    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        company.is_active = False
        company.updated_by = request.user
        company.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{company.company_name} was archived.')
        return redirect('company:company_list')


class CompanyRestoreView(CompanyLoginPermissionMixin, View):
    permission_required = CHANGE_COMPANY

    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        company.is_active = True
        company.updated_by = request.user
        company.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{company.company_name} was restored.')
        return redirect('company:company_list')
