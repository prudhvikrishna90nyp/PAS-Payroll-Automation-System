from django.contrib import admin, messages

from .models import PayPeriod, Payslip, PayslipItem
from .services import generate_payslips_for_period


class PayslipItemInline(admin.TabularInline):
    model = PayslipItem
    extra = 0
    readonly_fields = ('item_type', 'description', 'amount')


@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'start_date', 'end_date', 'is_closed')
    list_filter = ('year', 'is_closed')
    actions = ['generate_payslips']

    @admin.action(description='Generate payslips for selected periods')
    def generate_payslips(self, request, queryset):
        total = 0
        for pay_period in queryset:
            payslips = generate_payslips_for_period(pay_period)
            total += len(payslips)
        self.message_user(
            request,
            f'Generated {total} payslip(s).',
            messages.SUCCESS,
        )


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'pay_period',
        'gross_pay',
        'total_deductions',
        'net_pay',
        'status',
        'generated_at',
    )
    list_filter = ('status', 'pay_period')
    search_fields = ('employee__employee_code', 'employee__first_name', 'employee__last_name')
    inlines = [PayslipItemInline]
