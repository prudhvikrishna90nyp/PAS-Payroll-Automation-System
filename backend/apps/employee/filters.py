from django.db.models import Q

from .models import Employee


def filter_employees(queryset, params):
    """Apply list/search filters from a request GET dict."""
    search_query = params.get('q', '').strip()
    company_id = params.get('company', '').strip()
    branch_id = params.get('branch', '').strip()
    department_id = params.get('department', '').strip()
    designation_id = params.get('designation', '').strip()
    client_id = params.get('client', '').strip()
    status = params.get('status', '').strip()
    employment_status = params.get('employment_status', '').strip()
    employment_type = params.get('employment_type', '').strip()
    pf_eligible = params.get('pf_eligible', '').strip()
    esi_eligible = params.get('esi_eligible', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(employee_code__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(mobile__icontains=search_query)
            | Q(pan__icontains=search_query)
            | Q(aadhaar__icontains=search_query)
            | Q(uan__icontains=search_query)
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
    if employment_type:
        queryset = queryset.filter(employment_type=employment_type)
    if pf_eligible == 'yes':
        queryset = queryset.filter(pf_eligible=True)
    elif pf_eligible == 'no':
        queryset = queryset.filter(pf_eligible=False)
    if esi_eligible == 'yes':
        queryset = queryset.filter(esi_eligible=True)
    elif esi_eligible == 'no':
        queryset = queryset.filter(esi_eligible=False)

    return queryset


def employee_list_queryset(params=None):
    queryset = Employee.objects.select_related(
        'company',
        'company__client',
        'branch',
        'department',
        'designation',
    )
    if params is not None:
        queryset = filter_employees(queryset, params)
    return queryset.order_by('company__company_name', 'employee_code')
