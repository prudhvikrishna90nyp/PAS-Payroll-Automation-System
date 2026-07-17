from django.db.models import Q

from .models import (
    ComponentType,
    EmployeeSalaryAssignment,
    SalaryComponent,
    SalaryStructure,
)


def component_list_queryset(params):
    qs = SalaryComponent.objects.select_related('company', 'company__client').all()
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    component_type = (params.get('component_type') or '').strip()
    calc_type = (params.get('calculation_type') or '').strip()
    status = (params.get('status') or '').strip()

    if q:
        qs = qs.filter(
            Q(component_code__icontains=q)
            | Q(component_name__icontains=q)
            | Q(formula__icontains=q)
        )
    if company:
        qs = qs.filter(company_id=company)
    if component_type:
        qs = qs.filter(component_type=component_type)
    if calc_type:
        qs = qs.filter(calculation_type=calc_type)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    return qs


def structure_list_queryset(params):
    qs = SalaryStructure.objects.select_related('company', 'company__client').prefetch_related('lines')
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    status = (params.get('status') or '').strip()

    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q))
    if company:
        qs = qs.filter(company_id=company)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    return qs


def assignment_list_queryset(params):
    qs = EmployeeSalaryAssignment.objects.select_related(
        'employee',
        'employee__company',
        'salary_structure',
    )
    q = (params.get('q') or '').strip()
    company = (params.get('company') or '').strip()
    structure = (params.get('structure') or '').strip()
    current = (params.get('current') or '').strip()

    if q:
        qs = qs.filter(
            Q(employee__employee_code__icontains=q)
            | Q(employee__first_name__icontains=q)
            | Q(employee__last_name__icontains=q)
            | Q(salary_structure__code__icontains=q)
            | Q(salary_structure__name__icontains=q)
        )
    if company:
        qs = qs.filter(employee__company_id=company)
    if structure:
        qs = qs.filter(salary_structure_id=structure)
    if current == '1':
        qs = qs.filter(effective_to__isnull=True, is_active=True)
    elif current == '0':
        qs = qs.filter(effective_to__isnull=False)
    return qs


def component_type_choices():
    return ComponentType.choices
