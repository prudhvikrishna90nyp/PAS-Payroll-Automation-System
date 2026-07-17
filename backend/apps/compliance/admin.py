from django.contrib import admin

from apps.compliance.models import (
    EmployeeESIProfile,
    EmployeePFProfile,
    EmployeePTProfile,
    ESIRuleSet,
    PayrollESIResult,
    PayrollPFResult,
    PayrollPTResult,
    PFRuleSet,
    ProfessionalTaxRuleSet,
    ProfessionalTaxSlab,
)


class ProfessionalTaxSlabInline(admin.TabularInline):
    model = ProfessionalTaxSlab
    extra = 0
    ordering = ('sequence', 'salary_from')


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


@admin.register(ESIRuleSet)
class ESIRuleSetAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'effective_from',
        'effective_to',
        'eligibility_wage_limit',
        'employee_rate',
        'employer_rate',
        'daily_wage_exemption_limit',
        'rounding_method',
        'is_active',
    )
    list_filter = ('is_active', 'rounding_method')
    search_fields = ('code', 'name')
    ordering = ('-effective_from',)


@admin.register(EmployeeESIProfile)
class EmployeeESIProfileAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'ip_number',
        'is_esi_applicable',
        'is_daily_wage_worker',
        'joining_esi_date',
        'exit_esi_date',
        'covered_period_start',
    )
    list_filter = ('is_esi_applicable', 'is_daily_wage_worker')
    search_fields = (
        'ip_number',
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
    )
    autocomplete_fields = ('employee',)
    raw_id_fields = ('employee',)


@admin.register(PayrollESIResult)
class PayrollESIResultAdmin(admin.ModelAdmin):
    list_display = (
        'payroll_result',
        'rule_version',
        'esi_wages',
        'employee_esi',
        'employer_esi',
        'is_eligible',
        'continuity_applied',
        'missing_ip_number',
    )
    list_filter = ('rule_version', 'is_eligible', 'continuity_applied', 'missing_ip_number')
    search_fields = (
        'rule_version',
        'payroll_result__employee__employee_code',
    )
    readonly_fields = (
        'payroll_result',
        'rule_set',
        'rule_version',
        'esi_wages',
        'employee_esi',
        'employer_esi',
        'is_eligible',
        'above_wage_limit',
        'continuity_applied',
        'daily_wage_exemption',
        'missing_ip_number',
        'eligibility_notes',
        'calculation_detail',
        'created_at',
    )


@admin.register(ProfessionalTaxRuleSet)
class ProfessionalTaxRuleSetAdmin(admin.ModelAdmin):
    list_display = (
        'state_code',
        'name',
        'effective_from',
        'effective_to',
        'frequency',
        'special_month',
        'is_active',
    )
    list_filter = ('is_active', 'state_code', 'frequency')
    search_fields = ('state_code', 'name')
    ordering = ('state_code', '-effective_from')
    inlines = [ProfessionalTaxSlabInline]


@admin.register(ProfessionalTaxSlab)
class ProfessionalTaxSlabAdmin(admin.ModelAdmin):
    list_display = (
        'rule_set',
        'sequence',
        'salary_from',
        'salary_to',
        'tax_amount',
        'special_month_tax_amount',
    )
    list_filter = ('rule_set__state_code',)
    search_fields = ('rule_set__name', 'rule_set__state_code')
    autocomplete_fields = ('rule_set',)


@admin.register(EmployeePTProfile)
class EmployeePTProfileAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'state_code',
        'is_applicable',
        'exemption_type',
        'effective_from',
        'effective_to',
    )
    list_filter = ('is_applicable', 'state_code', 'exemption_type')
    search_fields = (
        'state_code',
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
    )
    autocomplete_fields = ('employee',)
    raw_id_fields = ('employee',)


@admin.register(PayrollPTResult)
class PayrollPTResultAdmin(admin.ModelAdmin):
    list_display = (
        'payroll_result',
        'state_code',
        'pt_wages',
        'tax_amount',
        'exemption_reason',
        'rule_set',
    )
    list_filter = ('state_code',)
    search_fields = (
        'state_code',
        'payroll_result__employee__employee_code',
    )
    readonly_fields = (
        'payroll_result',
        'rule_set',
        'state_code',
        'pt_wages',
        'tax_amount',
        'exemption_reason',
        'calculation_snapshot',
        'created_at',
    )
