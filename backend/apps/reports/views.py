from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.utils.http import urlencode

from apps.company.models import Department
from apps.employee.filters import employee_list_queryset
from apps.employee.models import Employee
from apps.employee.permissions import VIEW_EMPLOYEE
from apps.payroll.models import Payslip


@login_required
def reports_index(request):
    active_employees = Employee.objects.filter(is_active=True)
    return render(
        request,
        'reports/index.html',
        {
            'employee_count': active_employees.count(),
            'pf_employee_count': active_employees.filter(pf_eligible=True).count(),
            'esi_employee_count': active_employees.filter(esi_eligible=True).count(),
            'department_count': Department.objects.filter(is_active=True).count(),
            'payslip_count': Payslip.objects.count(),
        },
    )


def _employee_report(request, *, report_key, title, subtitle, params, show_statutory=False):
    employees = list(employee_list_queryset(params))
    export_params = dict(params)
    export_params['report'] = report_key
    return render(
        request,
        'reports/employee_report.html',
        {
            'report_title': title,
            'report_subtitle': subtitle,
            'employees': employees,
            'export_query': urlencode(export_params),
            'show_statutory': show_statutory,
        },
    )


@login_required
@permission_required(VIEW_EMPLOYEE, raise_exception=True)
def employee_register_report(request):
    return _employee_report(
        request,
        report_key='register',
        title='Employee Register',
        subtitle='Active employees across companies',
        params={'status': 'active'},
    )


@login_required
@permission_required(VIEW_EMPLOYEE, raise_exception=True)
def pf_employees_report(request):
    return _employee_report(
        request,
        report_key='pf',
        title='PF Eligible Employees',
        subtitle='Active employees marked PF eligible',
        params={'status': 'active', 'pf_eligible': 'yes'},
        show_statutory=True,
    )


@login_required
@permission_required(VIEW_EMPLOYEE, raise_exception=True)
def esi_employees_report(request):
    return _employee_report(
        request,
        report_key='esi',
        title='ESI Eligible Employees',
        subtitle='Active employees marked ESI eligible',
        params={'status': 'active', 'esi_eligible': 'yes'},
        show_statutory=True,
    )
