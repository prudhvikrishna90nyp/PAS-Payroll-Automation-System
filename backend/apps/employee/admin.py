from django.contrib import admin

from .models import Department, Employee


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('name', 'code')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id',
        'full_name',
        'department',
        'designation',
        'basic_salary',
        'is_active',
    )
    list_filter = ('department', 'is_active')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
