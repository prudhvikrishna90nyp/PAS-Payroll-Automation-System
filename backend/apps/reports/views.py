from django.shortcuts import render

from apps.company.models import Department
from apps.employee.models import Employee
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
