from django.contrib import admin

from .models import Employee, EmployeeDocument, SalaryStructure


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0
    fields = ('document_type', 'title', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    """Legacy simple structure (basic/HRA/transport). Prefer payroll.SalaryStructure."""

    list_display = ('code', 'name', 'company', 'basic_salary', 'is_active', 'is_deleted')

    list_filter = ('is_active', 'is_deleted', 'company')
    search_fields = ('name', 'code', 'company__company_name')
    readonly_fields = ('created_by', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_code',
        'full_name',
        'company',
        'department',
        'designation',
        'employment_type',
        'employment_status',
        'basic_salary',
        'is_active',
    )
    list_filter = (
        'is_active',
        'is_deleted',
        'employment_type',
        'employment_status',
        'company',
        'branch',
        'department',
        'pf_eligible',
        'esi_eligible',
    )
    search_fields = (
        'employee_code',
        'first_name',
        'last_name',
        'email',
        'mobile',
        'pan',
        'aadhaar',
    )
    readonly_fields = ('created_by', 'updated_by')
    inlines = [EmployeeDocumentInline]
    fieldsets = (
        ('Organisation', {
            'fields': (
                'company', 'branch', 'department', 'designation',
                'employee_code', 'auto_generate_code',
                'employment_type', 'employment_status', 'is_active',
            ),
        }),
        ('Personal', {
            'fields': (
                'first_name', 'last_name', 'email', 'mobile', 'alternate_mobile',
                'date_of_birth', 'gender', 'photo',
            ),
        }),
        ('Statutory IDs', {
            'fields': ('aadhaar', 'pan', 'uan', 'esic_number'),
        }),
        ('Bank Details', {
            'fields': (
                'bank_name', 'account_holder_name', 'bank_account_number', 'ifsc_code',
            ),
        }),
        ('Salary & Eligibility', {
            'fields': (
                'salary_structure', 'basic_salary', 'pf_eligible', 'esi_eligible',
            ),
        }),
        ('Employment Dates', {
            'fields': ('date_of_joining', 'date_of_exit'),
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name',
                'emergency_contact_phone',
                'emergency_contact_relation',
            ),
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'title', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('employee__employee_code', 'employee__first_name', 'title')
