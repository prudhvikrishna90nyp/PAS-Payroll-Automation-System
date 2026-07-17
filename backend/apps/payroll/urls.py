from django.urls import path

from . import views

app_name = 'payroll'

urlpatterns = [
    # Salary components
    path('components/', views.ComponentListView.as_view(), name='component_list'),
    path('components/add/', views.ComponentCreateView.as_view(), name='component_add'),
    path('components/seed/', views.SeedComponentsView.as_view(), name='component_seed'),
    path('components/<int:pk>/', views.ComponentDetailView.as_view(), name='component_detail'),
    path('components/<int:pk>/edit/', views.ComponentUpdateView.as_view(), name='component_edit'),
    path('components/<int:pk>/archive/', views.ComponentArchiveView.as_view(), name='component_archive'),

    # Structures
    path('structures/', views.StructureListView.as_view(), name='structure_list'),
    path('structures/add/', views.StructureCreateView.as_view(), name='structure_add'),
    path('structures/<int:pk>/', views.StructureDetailView.as_view(), name='structure_detail'),
    path('structures/<int:pk>/edit/', views.StructureUpdateView.as_view(), name='structure_edit'),
    path('structures/<int:pk>/archive/', views.StructureArchiveView.as_view(), name='structure_archive'),

    # Assignments
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/add/', views.AssignmentCreateView.as_view(), name='assignment_add'),
    path('assignments/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/<int:pk>/edit/', views.AssignmentUpdateView.as_view(), name='assignment_edit'),
    path('assignments/<int:pk>/archive/', views.AssignmentArchiveView.as_view(), name='assignment_archive'),

    # Payroll periods & runs (Sprint 8.1)
    path('periods/', views.PeriodListView.as_view(), name='period_list'),
    path('periods/add/', views.PeriodCreateView.as_view(), name='period_add'),
    path('periods/<int:pk>/', views.PeriodDetailView.as_view(), name='period_detail'),
    path('periods/<int:pk>/close/', views.PeriodCloseView.as_view(), name='period_close'),
    path('periods/<int:pk>/open/', views.PeriodOpenView.as_view(), name='period_open'),
    path('runs/', views.RunListView.as_view(), name='run_list'),
    path('runs/add/', views.RunCreateView.as_view(), name='run_add'),
    path('runs/<int:pk>/', views.RunDetailView.as_view(), name='run_detail'),
    path('runs/<int:pk>/calculate/', views.RunCalculateView.as_view(), name='run_calculate'),

    # Reports
    path('reports/', views.PayrollReportIndexView.as_view(), name='report_index'),
    path('reports/<str:report_type>/', views.PayrollReportDownloadView.as_view(), name='report_download'),

    # Payslips (legacy PayPeriod)
    path('payslips/', views.payslip_list, name='payslip_list'),
    path('payslips/<int:pk>/', views.payslip_detail, name='payslip_detail'),
    path('payslips/<int:pk>/pdf/', views.payslip_pdf, name='payslip_pdf'),
    path('payslips/export/', views.payslip_export_excel, name='payslip_export_excel'),
    path(
        'pay-periods/<int:period_id>/generate/',
        views.generate_period_payslips,
        name='generate_period_payslips',
    ),
]
