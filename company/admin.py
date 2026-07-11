from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'trade_name', 'state', 'phone', 'email', 'is_active')
    list_filter = ('is_active', 'state')
    search_fields = (
        'company_name',
        'trade_name',
        'pan',
        'gstin',
        'tan',
        'contact_person',
        'email',
    )
    fieldsets = (
        ('Company Details', {
            'fields': ('company_name', 'trade_name', 'logo', 'is_active'),
        }),
        ('Statutory Registration', {
            'fields': (
                'pan',
                'gstin',
                'tan',
                'epf_code',
                'esi_code',
                'professional_tax_registration',
                'labour_licence',
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
