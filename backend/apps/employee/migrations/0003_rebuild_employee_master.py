import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def assign_default_company(apps, schema_editor):
    Employee = apps.get_model('employee', 'Employee')
    Company = apps.get_model('company', 'Company')

    default_company = Company.objects.filter(company_name__iexact='Deep Enterprises').first()
    if not default_company:
        default_company = Company.objects.first()
    if default_company:
        Employee.objects.filter(company__isnull=True).update(company=default_company)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('company', '0006_organisation_structure'),
        ('employee', '0002_move_payroll_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalaryStructure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=20)),
                ('basic_salary', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                )),
                ('hra_percent', models.DecimalField(decimal_places=2, default=Decimal('40.00'), max_digits=5)),
                ('transport_allowance', models.DecimalField(decimal_places=2, default=Decimal('1600.00'), max_digits=12)),
                ('description', models.TextField(blank=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='salary_structures',
                    to='company.company',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='employee_salarystructure_created_records',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='employee_salarystructure_updated_records',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['company__company_name', 'name'],
                'unique_together': {('company', 'code')},
            },
        ),
        migrations.AddField(
            model_name='employee',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='employee',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='employee_id',
            new_name='employee_code',
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='date_joined',
            new_name='date_of_joining',
        ),
        migrations.AlterField(
            model_name='employee',
            name='employee_code',
            field=models.CharField(max_length=20, unique=False, verbose_name='Employee Code'),
        ),
        migrations.AddField(
            model_name='employee',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='employees',
                to='company.company',
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='auto_generate_code',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='mobile',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='employee',
            name='alternate_mobile',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='employee',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=10),
        ),
        migrations.AddField(
            model_name='employee',
            name='photo',
            field=models.ImageField(blank=True, upload_to='employee/photos/'),
        ),
        migrations.AddField(
            model_name='employee',
            name='aadhaar',
            field=models.CharField(blank=True, max_length=12, verbose_name='Aadhaar'),
        ),
        migrations.AddField(
            model_name='employee',
            name='uan',
            field=models.CharField(blank=True, max_length=12, verbose_name='UAN'),
        ),
        migrations.AddField(
            model_name='employee',
            name='esic_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='ESIC Number'),
        ),
        migrations.AddField(
            model_name='employee',
            name='bank_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='employee',
            name='bank_account_number',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='employee',
            name='ifsc_code',
            field=models.CharField(blank=True, max_length=11, verbose_name='IFSC'),
        ),
        migrations.AddField(
            model_name='employee',
            name='account_holder_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='employee',
            name='salary_structure',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employees',
                to='employee.salarystructure',
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='pf_eligible',
            field=models.BooleanField(default=True, verbose_name='PF Eligible'),
        ),
        migrations.AddField(
            model_name='employee',
            name='esi_eligible',
            field=models.BooleanField(default=False, verbose_name='ESI Eligible'),
        ),
        migrations.AddField(
            model_name='employee',
            name='date_of_exit',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='employment_status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('on_leave', 'On Leave'),
                    ('resigned', 'Resigned'),
                    ('terminated', 'Terminated'),
                    ('retired', 'Retired'),
                ],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='emergency_contact_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='employee',
            name='emergency_contact_phone',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='employee',
            name='emergency_contact_relation',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='employee',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employee_employee_created_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employee_employee_updated_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(
            model_name='employee',
            name='department',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='designation',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='bank_account',
        ),
        migrations.DeleteModel(
            name='Department',
        ),
        migrations.AddField(
            model_name='employee',
            name='branch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employees',
                to='company.branch',
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employees',
                to='company.department',
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='designation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employees',
                to='company.designation',
            ),
        ),
        migrations.AlterField(
            model_name='employee',
            name='last_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='employee',
            name='pan',
            field=models.CharField(blank=True, max_length=10, verbose_name='PAN'),
        ),
        migrations.RunPython(assign_default_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='employee',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='employees',
                to='company.company',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='employee',
            unique_together={('company', 'employee_code')},
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['employee_code'], name='employee_code_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['employment_status'], name='employee_status_idx'),
        ),
        migrations.AlterModelOptions(
            name='employee',
            options={'ordering': ['company__company_name', 'employee_code']},
        ),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(
                    choices=[
                        ('aadhaar', 'Aadhaar'),
                        ('pan', 'PAN Card'),
                        ('offer_letter', 'Offer Letter'),
                        ('appointment', 'Appointment Letter'),
                        ('bank_proof', 'Bank Proof'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=30,
                )),
                ('title', models.CharField(blank=True, max_length=200)),
                ('file', models.FileField(upload_to='employee/documents/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='employee.employee',
                )),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
