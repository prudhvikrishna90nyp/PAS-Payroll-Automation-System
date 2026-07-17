from django.urls import path

from .views import (
    EmployeeArchiveView,
    EmployeeCreateView,
    EmployeeDetailView,
    EmployeeExportView,
    EmployeeImportView,
    EmployeeListView,
    EmployeePdfExportView,
    EmployeeRestoreView,
    EmployeeUpdateView,
)

app_name = 'employees'

urlpatterns = [
    path('', EmployeeListView.as_view(), name='employee_list'),
    path('add/', EmployeeCreateView.as_view(), name='employee_add'),
    path('import/', EmployeeImportView.as_view(), name='employee_import'),
    path('export/', EmployeeExportView.as_view(), name='employee_export'),
    path('export/pdf/', EmployeePdfExportView.as_view(), name='employee_export_pdf'),
    path('<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('<int:pk>/archive/', EmployeeArchiveView.as_view(), name='employee_archive'),
    path('<int:pk>/restore/', EmployeeRestoreView.as_view(), name='employee_restore'),
]
