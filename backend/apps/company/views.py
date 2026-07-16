from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clients.models import Client
from apps.common.utils import paginate, status_filter

from .forms import BranchForm, CompanyForm
from .models import Branch, Company


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
    queryset = status_filter(queryset, request)
    page_obj = paginate(request, queryset)
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
    queryset = status_filter(queryset, request)
    page_obj = paginate(request, queryset)
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
