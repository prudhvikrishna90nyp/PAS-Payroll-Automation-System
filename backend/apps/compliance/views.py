"""Compliance UI — PF / ESI / PT / TDS registers and exports (Sprint 9.1–9.4)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.compliance.models import (
    EmployeeTaxProfile,
    InvestmentProof,
    PreviousEmployerIncome,
    TaxDeclaration,
    TaxDeclarationStatus,
    TaxRegime,
)
from apps.compliance.services.ecr_export import ecr_excel_response, ecr_text_response
from apps.compliance.services.esi_export import esi_contribution_excel_response
from apps.compliance.services.esi_reports import ESI_REPORT_EXPORTS
from apps.compliance.services.esi_rules import seed_default_esi_rule_set
from apps.compliance.services.form16_data import (
    build_form16_employee_payload,
    build_form16_run_payload,
    form16_excel_response,
)
from apps.compliance.services.pf_rules import seed_default_pf_rule_set
from apps.compliance.services.pt_export import pt_challan_excel_response
from apps.compliance.services.pt_reports import PT_REPORT_EXPORTS
from apps.compliance.services.pt_rules import seed_ap_pt_rule_set
from apps.compliance.services.reports import REPORT_EXPORTS
from apps.compliance.services.tds_export import tds_register_excel_response
from apps.compliance.services.tds_reports import TDS_REPORT_EXPORTS
from apps.compliance.services.tds_rules import seed_tds_rule_sets
from apps.employee.models import Employee
from apps.payroll.models import PayrollRun, PayrollRunStatus
from apps.payroll.services.report_queries import companies_visible_to_user


class ComplianceLoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class ComplianceHubView(ComplianceLoginPermissionMixin, View):
    permission_required = 'payroll.view_payrollrun'
    raise_exception = True

    def get(self, request):
        seed_default_pf_rule_set()
        seed_default_esi_rule_set()
        seed_ap_pt_rule_set()
        seed_tds_rule_sets()
        visible = companies_visible_to_user(request.user)
        runs = (
            PayrollRun.objects
            .filter(
                status__in=[
                    PayrollRunStatus.CALCULATED,
                    PayrollRunStatus.REVIEWED,
                    PayrollRunStatus.APPROVED,
                    PayrollRunStatus.LOCKED,
                ]
            )
            .select_related(
                'period', 'company',
                'pf_rule_set', 'esi_rule_set', 'pt_rule_set', 'tds_rule_set',
            )
            .order_by('-created_at')
        )
        if visible is not None:
            runs = runs.filter(company_id__in=visible)
        runs = runs[:50]
        return render(
            request,
            'compliance/hub.html',
            {
                'runs': runs,
                'report_keys': list(REPORT_EXPORTS.keys()),
                'esi_report_keys': list(ESI_REPORT_EXPORTS.keys()),
                'pt_report_keys': list(PT_REPORT_EXPORTS.keys()),
                'tds_report_keys': list(TDS_REPORT_EXPORTS.keys()),
            },
        )


class PFReportExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_pfregister'
    raise_exception = True

    def get(self, request, run_id, report_key):
        if report_key not in REPORT_EXPORTS:
            messages.error(request, 'Unknown PF report.')
            return redirect('compliance:hub')
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        return REPORT_EXPORTS[report_key](run)


class ESIReportExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_esiregister'
    raise_exception = True

    def get(self, request, run_id, report_key):
        if report_key not in ESI_REPORT_EXPORTS:
            messages.error(request, 'Unknown ESI report.')
            return redirect('compliance:hub')
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        return ESI_REPORT_EXPORTS[report_key](run)


class ESIContributionExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_esicontribution'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        require_ip = request.GET.get('validate', '1') != '0'
        try:
            return esi_contribution_excel_response(run, require_ip=require_ip)
        except ValidationError as exc:
            messages.error(
                request,
                '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
            )
            return redirect(reverse('compliance:hub'))


class PTReportExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_ptregister'
    raise_exception = True

    def get(self, request, run_id, report_key):
        if report_key not in PT_REPORT_EXPORTS:
            messages.error(request, 'Unknown PT report.')
            return redirect('compliance:hub')
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        return PT_REPORT_EXPORTS[report_key](run)


class PTChallanExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_ptchallan'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        try:
            return pt_challan_excel_response(run)
        except ValidationError as exc:
            messages.error(
                request,
                '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
            )
            return redirect(reverse('compliance:hub'))


class TDSReportExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_tdsregister'
    raise_exception = True

    def get(self, request, run_id, report_key):
        if report_key not in TDS_REPORT_EXPORTS:
            messages.error(request, 'Unknown TDS report.')
            return redirect('compliance:hub')
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        return TDS_REPORT_EXPORTS[report_key](run)


class TDSRegisterExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_tdsregister'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        try:
            return tds_register_excel_response(run)
        except ValidationError as exc:
            messages.error(
                request,
                '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
            )
            return redirect(reverse('compliance:hub'))


class Form16PreviewView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_form16'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        employee_id = request.GET.get('employee')
        employee = None
        payload = None
        payloads = []
        try:
            if employee_id:
                employee = get_object_or_404(Employee, pk=employee_id, company=run.company)
                payload = build_form16_employee_payload(run, employee)
            else:
                payloads = build_form16_run_payload(run)
        except ValidationError as exc:
            messages.error(
                request,
                '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
            )
        return render(
            request,
            'compliance/form16_preview.html',
            {
                'run': run,
                'employee': employee,
                'payload': payload,
                'payloads': payloads,
            },
        )


class Form16ExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_form16'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        employee = None
        employee_id = request.GET.get('employee')
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id, company=run.company)
        try:
            return form16_excel_response(run, employee=employee)
        except ValidationError as exc:
            messages.error(
                request,
                '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc),
            )
            return redirect(reverse('compliance:hub'))


class ECRExportView(ComplianceLoginPermissionMixin, View):
    permission_required = 'compliance.export_ecr'
    raise_exception = True

    def get(self, request, run_id):
        run = get_object_or_404(
            PayrollRun.objects.select_related('period', 'company'),
            pk=run_id,
        )
        visible = companies_visible_to_user(request.user)
        if visible is not None and run.company_id not in visible:
            raise PermissionDenied
        fmt = request.GET.get('format', 'txt')
        validate = request.GET.get('validate', '1') != '0'
        try:
            if fmt == 'xlsx':
                return ecr_excel_response(run, validate_uans=validate)
            return ecr_text_response(run, validate_uans=validate)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
            return redirect(reverse('compliance:hub'))


class TaxProfileListView(ComplianceLoginPermissionMixin, View):
    permission_required = 'payroll.view_payrollrun'
    raise_exception = True

    def get(self, request):
        seed_tds_rule_sets()
        visible = companies_visible_to_user(request.user)
        qs = EmployeeTaxProfile.objects.select_related('employee', 'employee__company')
        if visible is not None:
            qs = qs.filter(employee__company_id__in=visible)
        return render(
            request,
            'compliance/tax_profiles.html',
            {'profiles': qs.order_by('employee__employee_code')[:200]},
        )


class TaxDeclarationListView(ComplianceLoginPermissionMixin, View):
    permission_required = 'payroll.view_payrollrun'
    raise_exception = True

    def get(self, request):
        visible = companies_visible_to_user(request.user)
        qs = TaxDeclaration.objects.select_related('employee', 'employee__company')
        if visible is not None:
            qs = qs.filter(employee__company_id__in=visible)
        fy = request.GET.get('fy') or ''
        if fy:
            qs = qs.filter(financial_year=fy)
        return render(
            request,
            'compliance/tax_declarations.html',
            {
                'declarations': qs.order_by('-financial_year', 'employee__employee_code')[:200],
                'fy': fy,
                'statuses': TaxDeclarationStatus.choices,
                'regimes': TaxRegime.choices,
            },
        )


class InvestmentProofListView(ComplianceLoginPermissionMixin, View):
    permission_required = 'payroll.view_payrollrun'
    raise_exception = True

    def get(self, request):
        visible = companies_visible_to_user(request.user)
        qs = InvestmentProof.objects.select_related('employee', 'declaration')
        if visible is not None:
            qs = qs.filter(employee__company_id__in=visible)
        return render(
            request,
            'compliance/investment_proofs.html',
            {'proofs': qs.order_by('-created_at')[:200]},
        )


class PreviousEmployerListView(ComplianceLoginPermissionMixin, View):
    permission_required = 'payroll.view_payrollrun'
    raise_exception = True

    def get(self, request):
        visible = companies_visible_to_user(request.user)
        qs = PreviousEmployerIncome.objects.select_related('employee')
        if visible is not None:
            qs = qs.filter(employee__company_id__in=visible)
        return render(
            request,
            'compliance/previous_employer.html',
            {'rows': qs.order_by('-financial_year')[:200]},
        )
