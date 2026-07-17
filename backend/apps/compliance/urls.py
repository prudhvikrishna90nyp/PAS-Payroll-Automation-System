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
        'runs/<int:run_id>/esi-reports/<slug:report_key>/',
        views.ESIReportExportView.as_view(),
        name='esi_report_export',
    ),
    path(
        'runs/<int:run_id>/esi-contribution/',
        views.ESIContributionExportView.as_view(),
        name='esi_contribution_export',
    ),
    path(
        'runs/<int:run_id>/pt-reports/<slug:report_key>/',
        views.PTReportExportView.as_view(),
        name='pt_report_export',
    ),
    path(
        'runs/<int:run_id>/pt-challan/',
        views.PTChallanExportView.as_view(),
        name='pt_challan_export',
    ),
    path(
        'runs/<int:run_id>/ecr/',
        views.ECRExportView.as_view(),
        name='ecr_export',
    ),
]
