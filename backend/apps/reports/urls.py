from django.urls import path

from . import views

urlpatterns = [
    path('', views.reports_index, name='reports_index'),
    path('employees/register/', views.employee_register_report, name='employee_register_report'),
    path('employees/pf/', views.pf_employees_report, name='pf_employees_report'),
    path('employees/esi/', views.esi_employees_report, name='esi_employees_report'),
]
