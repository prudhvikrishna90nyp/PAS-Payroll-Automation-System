# Generated manually for Sprint 9.1 EPF compliance

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models

import apps.common.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('employee', '0006_alter_salarystructure_hra_percent'),
        ('payroll', '0005_payroll_approval_locking_sprint83'),
    ]

    operations = [
        migrations.CreateModel(
            name='PFRuleSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='India EPF', max_length=100)),
                ('code', models.CharField(help_text='Stable identifier snapshotted on payroll results (e.g. IN-EPF-2024).', max_length=30, unique=True)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, help_text='Inclusive end date. Null means open-ended.', null=True)),
                ('pf_wage_ceiling', models.DecimalField(decimal_places=2, default=Decimal('15000.00'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('employee_pf_rate', models.DecimalField(decimal_places=4, default=Decimal('0.1200'), help_text='Employee EPF rate as a fraction (0.12 = 12%).', max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('employer_pf_rate', models.DecimalField(decimal_places=4, default=Decimal('0.1200'), help_text='Total employer contribution rate (EPS + employer EPF).', max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('eps_rate', models.DecimalField(decimal_places=4, default=Decimal('0.0833'), help_text='EPS share of employer contribution (typically 8.33%).', max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('edli_rate', models.DecimalField(decimal_places=4, default=Decimal('0.0050'), max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('admin_charge', models.DecimalField(decimal_places=4, default=Decimal('0.0050'), max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('inspection_charge', models.DecimalField(decimal_places=4, default=Decimal('0.0000'), max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'PF Rule Set',
                'verbose_name_plural': 'PF Rule Sets',
                'ordering': ['-effective_from', 'code'],
                'permissions': [('export_pfregister', 'Can export PF registers'), ('export_ecr', 'Can export EPFO ECR')],
            },
        ),
        migrations.CreateModel(
            name='EmployeePFProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uan', models.CharField(blank=True, max_length=12, validators=[apps.common.validators.validate_uan])),
                ('pf_number', models.CharField(blank=True, max_length=50)),
                ('joining_pf_date', models.DateField(blank=True, null=True)),
                ('exit_pf_date', models.DateField(blank=True, null=True)),
                ('higher_pension', models.BooleanField(default=False, help_text='If set, EPS is computed on actual PF wages without the statutory ceiling.')),
                ('voluntary_pf', models.BooleanField(default=False)),
                ('vpf_percentage', models.DecimalField(decimal_places=4, default=Decimal('0.0000'), help_text='Voluntary PF as a fraction of PF wages (e.g. 0.05 = 5%).', max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('1'))])),
                ('is_pf_applicable', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pf_profile', to='employee.employee')),
            ],
            options={
                'verbose_name': 'Employee PF Profile',
                'verbose_name_plural': 'Employee PF Profiles',
                'ordering': ['employee__employee_code'],
            },
        ),
        migrations.CreateModel(
            name='PayrollPFResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rule_version', models.CharField(blank=True, help_text='Denormalised PFRuleSet.code at calculation time.', max_length=30)),
                ('pf_wages', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('actual_pf_wages', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Sum of PF-applicable earnings before ceiling.', max_digits=12)),
                ('employee_pf', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('voluntary_pf', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('employer_pf', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total employer contribution (EPS + employer EPF).', max_digits=12)),
                ('eps', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('epf', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Employer EPF account share (employer_pf - eps).', max_digits=12)),
                ('edli', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('admin_charge', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('inspection_charge', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('ncp_days', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Non-contributory days (typically LOP) for ECR.', max_digits=6)),
                ('calculation_detail', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('payroll_result', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pf_result', to='payroll.payrollresult')),
                ('rule_set', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payroll_pf_results', to='compliance.pfruleset')),
            ],
            options={
                'verbose_name': 'Payroll PF Result',
                'verbose_name_plural': 'Payroll PF Results',
                'ordering': ['payroll_result_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='employeepfprofile',
            constraint=models.UniqueConstraint(condition=models.Q(('pf_number', ''), _negated=True), fields=('pf_number',), name='uniq_employee_pf_number_nonblank'),
        ),
    ]
