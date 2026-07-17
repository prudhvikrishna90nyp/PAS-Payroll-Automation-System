from django.contrib import admin

from .models import Branch, Company, Department, Designation


class OrganisationAdminMixin:
    readonly_fields = ('created_by', 'updated_by')
    list_filter = ('is_active', 'is_deleted', 'company')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'client', 'trade_name', 'state', 'phone', 'is_active', 'is_deleted')
    list_filter = ('is_active', 'is_deleted', 'client', 'state')
    search_fields = ('company_name', 'trade_name', 'pan', 'gstin', 'tan', 'email')
    fieldsets = (
        ('Company Details', {
            'fields': ('client', 'company_name', 'trade_name', 'logo', 'is_active'),
        }),
        ('Statutory Registration', {
            'fields': (
                'pan', 'gstin', 'tan', 'epf_code', 'esi_code',
                'professional_tax_registration', 'labour_licence',
            ),
        }),
        ('Address', {
            'fields': ('address', 'state', 'district', 'pin_code'),
        }),
        ('Contact', {
            'fields': ('contact_person', 'phone', 'email'),
        }),
        ('Banking', {
            'fields': ('bank_details',),
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_by', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Branch)
class BranchAdmin(OrganisationAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'branch_name', 'company', 'state', 'is_head_office', 'is_active', 'is_deleted')
    search_fields = ('branch_name', 'code', 'company__company_name')
    fieldsets = (
        ('Branch Details', {
            'fields': ('company', 'branch_name', 'code', 'is_head_office', 'is_active'),
        }),
        ('Address', {
            'fields': ('address', 'state', 'district', 'pin_code'),
        }),
        ('Contact', {
            'fields': ('contact_person', 'phone', 'email'),
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Department)
class DepartmentAdmin(OrganisationAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'is_active', 'is_deleted')
    search_fields = ('name', 'code', 'company__company_name')
    fieldsets = (
        ('Department Details', {
            'fields': ('company', 'name', 'code', 'description', 'is_active'),
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Designation)
class DesignationAdmin(OrganisationAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'is_active', 'is_deleted')
    search_fields = ('name', 'code', 'company__company_name')
    fieldsets = (
        ('Designation Details', {
            'fields': ('company', 'name', 'code', 'description', 'is_active'),
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
