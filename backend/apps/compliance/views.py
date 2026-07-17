"""Compliance UI — PF / ESI / PT registers and exports (Sprint 9.1–9.3)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.compliance.services.ecr_export import ecr_excel_response, ecr_text_response
from apps.compliance.services.esi_export import esi_contribution_excel_response
from apps.compliance.services.esi_reports import ESI_REPORT_EXPORTS
from apps.compliance.services.esi_rules import seed_default_esi_rule_set
from apps.compliance.services.pf_rules import seed_default_pf_rule_set
from apps.compliance.services.pt_export import pt_challan_excel_response
from apps.compliance.services.pt_reports import PT_REPORT_EXPORTS
from apps.compliance.services.pt_rules import seed_ap_pt_rule_set
from apps.compliance.services.reports import REPORT_EXPORTS
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
            .select_related('period', 'company', 'pf_rule_set', 'esi_rule_set', 'pt_rule_set')
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
