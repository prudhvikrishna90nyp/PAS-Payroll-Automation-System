from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ClientForm
from .models import Client
from .permissions import ADD_CLIENT, CHANGE_CLIENT, DELETE_CLIENT, VIEW_CLIENT


class ClientLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class ClientListView(ClientLoginPermissionMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10
    permission_required = VIEW_CLIENT

    def get_queryset(self):
        queryset = Client.objects.all()

        search_query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(client_code__icontains=search_query)
                | Q(client_name__icontains=search_query)
                | Q(trade_name__icontains=search_query)
                | Q(contact_person__icontains=search_query)
                | Q(mobile__icontains=search_query)
                | Q(pan__icontains=search_query)
                | Q(gstin__icontains=search_query)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('client_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class ClientDetailView(ClientLoginPermissionMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'
    permission_required = VIEW_CLIENT


class ClientCreateView(ClientLoginPermissionMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')
    permission_required = ADD_CLIENT

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Client created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class ClientUpdateView(ClientLoginPermissionMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')
    permission_required = CHANGE_CLIENT

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Client updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors shown below.')
        return super().form_invalid(form)


class ClientArchiveView(ClientLoginPermissionMixin, View):
    permission_required = DELETE_CLIENT

    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        client.is_active = False
        client.updated_by = request.user
        client.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{client.client_name} was archived.')
        return redirect('clients:client_list')


class ClientRestoreView(ClientLoginPermissionMixin, View):
    permission_required = CHANGE_CLIENT

    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        client.is_active = True
        client.updated_by = request.user
        client.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f'{client.client_name} was restored.')
        return redirect('clients:client_list')
