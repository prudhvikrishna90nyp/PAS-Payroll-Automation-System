import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('employee', '0002_move_payroll_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='PayPeriod',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('year', models.PositiveIntegerField()),
                        ('month', models.PositiveIntegerField()),
                        ('start_date', models.DateField()),
                        ('end_date', models.DateField()),
                        ('is_closed', models.BooleanField(default=False)),
                    ],
                    options={
                        'db_table': 'employees_payperiod',
                        'ordering': ['-year', '-month'],
                        'unique_together': {('year', 'month')},
                    },
                ),
                migrations.CreateModel(
                    name='Payslip',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('basic_salary', models.DecimalField(decimal_places=2, max_digits=12)),
                        ('gross_pay', models.DecimalField(decimal_places=2, max_digits=12)),
                        ('total_deductions', models.DecimalField(decimal_places=2, max_digits=12)),
                        ('net_pay', models.DecimalField(decimal_places=2, max_digits=12)),
                        ('status', models.CharField(choices=[('draft', 'Draft'), ('finalized', 'Finalized')], default='draft', max_length=20)),
                        ('generated_at', models.DateTimeField(auto_now_add=True)),
                        ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='employee.employee')),
                        ('pay_period', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='payroll.payperiod')),
                    ],
                    options={
                        'db_table': 'employees_payslip',
                        'ordering': ['-pay_period__year', '-pay_period__month', 'employee__employee_id'],
                        'unique_together': {('employee', 'pay_period')},
                    },
                ),
                migrations.CreateModel(
                    name='PayslipItem',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('item_type', models.CharField(choices=[('earning', 'Earning'), ('deduction', 'Deduction')], max_length=20)),
                        ('description', models.CharField(max_length=100)),
                        ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                        ('payslip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='payroll.payslip')),
                    ],
                    options={
                        'db_table': 'employees_payslipitem',
                        'ordering': ['item_type', 'description'],
                    },
                ),
            ],
        ),
    ]
