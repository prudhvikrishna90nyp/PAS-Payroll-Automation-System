from django.contrib import admin

from .models import (
    EmployeeSalaryAssignment,
    PayPeriod,
    PayrollAuditLog,
    PayrollPeriod,
    PayrollResult,
    PayrollResultComponent,
    PayrollRun,
    Payslip,
    PayslipItem,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)


class PayslipItemInline(admin.TabularInline):
    model = PayslipItem
    extra = 0


@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'start_date', 'end_date', 'is_closed')
    list_filter = ('year', 'is_closed')


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'pay_period',
        'basic_salary',
        'gross_pay',
        'total_deductions',
        'net_pay',
        'status',
    )
    list_filter = ('status', 'pay_period')
    search_fields = ('employee__employee_code', 'employee__first_name', 'employee__last_name')
    inlines = [PayslipItemInline]


class SalaryStructureLineInline(admin.TabularInline):
    model = SalaryStructureLine
    extra = 1
    autocomplete_fields = ('component',)


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = (
        'component_code',
        'component_name',
        'company',
        'component_type',
        'calculation_type',
        'display_order',
        'is_active',
    )
    list_filter = ('company', 'component_type', 'calculation_type', 'is_active')
    search_fields = ('component_code', 'component_name', 'formula')
    ordering = ('company__company_name', 'display_order', 'component_code')


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'is_active', 'created_at')
    list_filter = ('company', 'is_active')
    search_fields = ('code', 'name', 'description')
    inlines = [SalaryStructureLineInline]


@admin.register(SalaryStructureLine)
class SalaryStructureLineAdmin(admin.ModelAdmin):
    list_display = (
        'structure',
        'component',
        'calculation_type',
        'value',
        'percent',
        'display_order',
    )
    list_filter = ('structure__company', 'calculation_type')
    search_fields = ('structure__code', 'component__component_code')
    autocomplete_fields = ('structure', 'component')


@admin.register(EmployeeSalaryAssignment)
class EmployeeSalaryAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'salary_structure',
        'effective_from',
        'effective_to',
        'gross_salary',
        'ctc',
        'is_active',
    )
    list_filter = ('employee__company', 'salary_structure', 'is_active')
    search_fields = (
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
        'salary_structure__code',
    )
    autocomplete_fields = ('employee', 'salary_structure')
    date_hierarchy = 'effective_from'


class PayrollResultComponentInline(admin.TabularInline):
    model = PayrollResultComponent
    extra = 0


class PayrollResultInline(admin.TabularInline):
    model = PayrollResult
    extra = 0
    show_change_link = True
    fields = (
        'employee',
        'present_days',
        'lop_days',
        'gross',
        'total_deductions',
        'net_salary',
    )
    autocomplete_fields = ('employee',)


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'month',
        'year',
        'start_date',
        'end_date',
        'status',
        'created_at',
    )
    list_filter = ('status', 'year', 'company')
    search_fields = ('company__company_name',)
    date_hierarchy = 'start_date'


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'period',
        'run_number',
        'status',
        'pf_rule_set',
        'esi_rule_set',
        'pt_rule_set',
        'created_by',
        'created_at',
    )
    list_filter = ('status', 'company', 'period__year')
    search_fields = ('company__company_name', 'notes')
    autocomplete_fields = (
        'period', 'company', 'created_by', 'pf_rule_set', 'esi_rule_set', 'pt_rule_set',
    )
    readonly_fields = ('calculation_errors',)
    inlines = [PayrollResultInline]


@admin.register(PayrollResult)
class PayrollResultAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'run',
        'present_days',
        'lop_days',
        'gross',
        'total_deductions',
        'net_salary',
    )
    list_filter = ('run__company', 'run__period')
    search_fields = (
        'employee__employee_code',
        'employee__first_name',
        'employee__last_name',
    )
    autocomplete_fields = ('run', 'employee')
    inlines = [PayrollResultComponentInline]


@admin.register(PayrollResultComponent)
class PayrollResultComponentAdmin(admin.ModelAdmin):
    list_display = (
        'result',
        'component_code',
        'component_name',
        'component_type',
        'amount',
    )
    list_filter = ('component_type',)
    search_fields = ('component_code', 'component_name')


@admin.register(PayrollAuditLog)
class PayrollAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'period', 'run', 'user', 'timestamp')
    list_filter = ('action',)
    search_fields = ('action', 'user__username')
    readonly_fields = ('period', 'run', 'action', 'user', 'timestamp', 'details')
    date_hierarchy = 'timestamp'
