from django.urls import path

from . import views

app_name = 'compliance'

urlpatterns = [
    path('', views.ComplianceHubView.as_view(), name='hub'),
    path(
        'runs/<int:run_id>/reports/<slug:report_key>/',
        views.PFReportExportView.as_view(),
        name='pf_report_export',
    ),
    path(
        'runs/<int:run_id>/ecr/',
        views.ECRExportView.as_view(),
        name='ecr_export',
    ),
]
