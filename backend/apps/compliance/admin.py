from django.contrib import admin

from apps.compliance.models import EmployeePFProfile, PayrollPFResult, PFRuleSet


@admin.register(PFRuleSet)
class PFRuleSetAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'effective_from',
        'effective_to',
        'pf_wage_ceiling',
        'employee_pf_rate',
        'employer_pf_rate',
        'eps_rate',
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    ordering = ('-effective_from',)


@admin.register(EmployeePFProfile)
class EmployeePFProfileAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'uan',
        'pf_number',
        'is_pf_applicable',
        'higher_pension',
        'voluntary_pf',
        'vpf_percentage',
    )
    list_filter = ('is_pf_applicable', 'higher_pension', 'voluntary_pf')
    search_fields = (
        'uan',
        'pf_number',
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
    )
    autocomplete_fields = ('employee',)
    raw_id_fields = ('employee',)


@admin.register(PayrollPFResult)
class PayrollPFResultAdmin(admin.ModelAdmin):
    list_display = (
        'payroll_result',
        'rule_version',
        'pf_wages',
        'employee_pf',
        'employer_pf',
        'eps',
        'epf',
    )
    list_filter = ('rule_version',)
    search_fields = (
        'rule_version',
        'payroll_result__employee__employee_code',
    )
    readonly_fields = (
        'payroll_result',
        'rule_set',
        'rule_version',
        'pf_wages',
        'actual_pf_wages',
        'employee_pf',
        'voluntary_pf',
        'employer_pf',
        'eps',
        'epf',
        'edli',
        'admin_charge',
        'inspection_charge',
        'ncp_days',
        'calculation_detail',
        'created_at',
    )
