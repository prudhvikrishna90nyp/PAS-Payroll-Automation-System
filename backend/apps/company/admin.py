from django.contrib import admin

from .models import Branch, Client, Company


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_person', 'phone', 'is_active', 'is_deleted')
    list_filter = ('is_active', 'is_deleted')
    search_fields = ('name', 'code', 'email')


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
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_name', 'code', 'company', 'state', 'is_head_office', 'is_active', 'is_deleted')
    list_filter = ('is_active', 'is_deleted', 'is_head_office', 'company')
    search_fields = ('branch_name', 'code', 'company__company_name')
