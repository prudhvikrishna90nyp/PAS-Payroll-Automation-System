from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BranchForm, ClientForm, CompanyForm
from .models import Branch, Client, Company

PAGE_SIZE = 10


def _paginate(request, queryset):
    paginator = Paginator(queryset, PAGE_SIZE)
    return paginator.get_page(request.GET.get('page'))


def _status_filter(queryset, request):
    status = request.GET.get('status')
    if status == 'active':
        return queryset.filter(is_active=True)
    if status == 'inactive':
        return queryset.filter(is_active=False)
    return queryset


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
    queryset = _status_filter(queryset, request)
    page_obj = _paginate(request, queryset)
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'company/client_list.html', {
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
    return render(request, 'company/client_form.html', {
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
    return render(request, 'company/client_form.html', {
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


@login_required
def company_list(request):
    queryset = Company.objects.select_related('client')
    q = request.GET.get('q', '').strip()
    client_id = request.GET.get('client')
    if q:
        queryset = queryset.filter(
            Q(company_name__icontains=q)
            | Q(trade_name__icontains=q)
            | Q(pan__icontains=q)
            | Q(gstin__icontains=q)
        )
    if client_id:
        queryset = queryset.filter(client_id=client_id)
    queryset = _status_filter(queryset, request)
    page_obj = _paginate(request, queryset)
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'company/company_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': request.GET.get('status', ''),
        'client_id': client_id or '',
        'clients': Client.objects.filter(is_active=True),
        'filter_query': params.urlencode(),
    })


@login_required
def company_create(request):
    form = CompanyForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Company created successfully.')
        return redirect('company_list')
    return render(request, 'company/company_form.html', {
        'form': form,
        'title': 'Add Company',
    })


@login_required
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    form = CompanyForm(request.POST or None, request.FILES or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Company updated successfully.')
        return redirect('company_list')
    return render(request, 'company/company_form.html', {
        'form': form,
        'title': 'Edit Company',
        'object': company,
    })


@login_required
@require_POST
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.soft_delete()
    messages.success(request, f'Company "{company.company_name}" deleted.')
    return redirect('company_list')


@login_required
def branch_list(request):
    queryset = Branch.objects.select_related('company', 'company__client')
    q = request.GET.get('q', '').strip()
    company_id = request.GET.get('company')
    client_id = request.GET.get('client')
    if q:
        queryset = queryset.filter(
            Q(branch_name__icontains=q)
            | Q(code__icontains=q)
            | Q(company__company_name__icontains=q)
        )
    if company_id:
        queryset = queryset.filter(company_id=company_id)
    if client_id:
        queryset = queryset.filter(company__client_id=client_id)
    queryset = _status_filter(queryset, request)
    page_obj = _paginate(request, queryset)
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'company/branch_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': request.GET.get('status', ''),
        'company_id': company_id or '',
        'client_id': client_id or '',
        'clients': Client.objects.filter(is_active=True),
        'companies': Company.objects.filter(is_active=True),
        'filter_query': params.urlencode(),
    })


@login_required
def branch_create(request):
    form = BranchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Branch created successfully.')
        return redirect('branch_list')
    return render(request, 'company/branch_form.html', {
        'form': form,
        'title': 'Add Branch',
    })


@login_required
def branch_update(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    form = BranchForm(request.POST or None, instance=branch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Branch updated successfully.')
        return redirect('branch_list')
    return render(request, 'company/branch_form.html', {
        'form': form,
        'title': 'Edit Branch',
        'object': branch,
    })


@login_required
@require_POST
def branch_delete(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    branch.soft_delete()
    messages.success(request, f'Branch "{branch.branch_name}" deleted.')
    return redirect('branch_list')
