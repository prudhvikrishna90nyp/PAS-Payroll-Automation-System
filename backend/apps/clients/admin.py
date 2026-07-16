from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'client_code',
        'client_name',
        'contact_person',
        'mobile',
        'state',
        'gstin',
        'is_active',
        'updated_at',
    )

    search_fields = (
        'client_code',
        'client_name',
        'trade_name',
        'contact_person',
        'mobile',
        'pan',
        'gstin',
    )

    list_filter = (
        'is_active',
        'state',
        'created_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
    )

    ordering = ('client_name',)
    list_per_page = 25

    fieldsets = (
        (
            'Client Information',
            {
                'fields': (
                    'client_code',
                    'client_name',
                    'trade_name',
                    'contact_person',
                    'is_active',
                )
            },
        ),
        (
            'Contact Information',
            {
                'fields': (
                    'mobile',
                    'alternate_mobile',
                    'email',
                )
            },
        ),
        (
            'Registration Information',
            {
                'fields': (
                    'pan',
                    'gstin',
                )
            },
        ),
        (
            'Address',
            {
                'fields': (
                    'address_line_1',
                    'address_line_2',
                    'city',
                    'district',
                    'state',
                    'pincode',
                )
            },
        ),
        (
            'Additional Information',
            {
                'fields': ('notes',),
            },
        ),
        (
            'Audit Information',
            {
                'classes': ('collapse',),
                'fields': (
                    'created_at',
                    'updated_at',
                    'created_by',
                    'updated_by',
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
