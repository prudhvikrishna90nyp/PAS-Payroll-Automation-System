from django.urls import path

from . import views

app_name = 'compliance'

urlpatterns = [
    path('', views.ComplianceHubView.as_view(), name='hub'),
    path('tax-profiles/', views.TaxProfileListView.as_view(), name='tax_profiles'),
    path('tax-declarations/', views.TaxDeclarationListView.as_view(), name='tax_declarations'),
    path('investment-proofs/', views.InvestmentProofListView.as_view(), name='investment_proofs'),
    path('previous-employer/', views.PreviousEmployerListView.as_view(), name='previous_employer'),
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
        'runs/<int:run_id>/tds-reports/<slug:report_key>/',
        views.TDSReportExportView.as_view(),
        name='tds_report_export',
    ),
    path(
        'runs/<int:run_id>/tds-register/',
        views.TDSRegisterExportView.as_view(),
        name='tds_register_export',
    ),
    path(
        'runs/<int:run_id>/form16/',
        views.Form16PreviewView.as_view(),
        name='form16_preview',
    ),
    path(
        'runs/<int:run_id>/form16/export/',
        views.Form16ExportView.as_view(),
        name='form16_export',
    ),
    path(
        'runs/<int:run_id>/ecr/',
        views.ECRExportView.as_view(),
        name='ecr_export',
    ),
]
