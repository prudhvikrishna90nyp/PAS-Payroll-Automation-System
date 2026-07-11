from django.shortcuts import render

from .models import Employee


def employee_list(request):
    employees = Employee.objects.select_related('department').filter(is_active=True)
    return render(
        request,
        'employee/employee_list.html',
        {'employees': employees},
    )
