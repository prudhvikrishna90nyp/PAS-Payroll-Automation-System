from django.urls import path

from . import views

urlpatterns = [
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
