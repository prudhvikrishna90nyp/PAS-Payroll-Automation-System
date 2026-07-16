from django.shortcuts import render

from apps.employee.models import Department, Employee
from apps.payroll.models import Payslip


def reports_index(request):
    return render(
        request,
        'reports/index.html',
        {
            'employee_count': Employee.objects.filter(is_active=True).count(),
            'department_count': Department.objects.count(),
            'payslip_count': Payslip.objects.count(),
        },
    )
