from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.utils import paginate, status_filter

from .forms import ClientForm
from .models import Client


@login_required
def client_list(request):
    queryset = Client.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(contact_person__icontains=q)
            | Q(email__icontains=q)
        )
    queryset = status_filter(queryset, request)
    page_obj = paginate(request, queryset)
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'clients/client_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': request.GET.get('status', ''),
        'filter_query': params.urlencode(),
    })


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Client created successfully.')
        return redirect('client_list')
    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': 'Add Client',
    })


@login_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Client updated successfully.')
        return redirect('client_list')
    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': 'Edit Client',
        'object': client,
    })


@login_required
@require_POST
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    client.soft_delete()
    messages.success(request, f'Client "{client.name}" deleted.')
    return redirect('client_list')
