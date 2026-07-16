from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_person', 'phone', 'is_active', 'is_deleted')
    list_filter = ('is_active', 'is_deleted')
    search_fields = ('name', 'code', 'email')
