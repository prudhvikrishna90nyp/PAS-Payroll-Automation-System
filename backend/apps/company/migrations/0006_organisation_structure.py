import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('company', '0005_company_audit_and_deep_enterprises'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='company_branch_created_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='branch',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='company_branch_updated_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='departments',
                    to='company.company',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='company_department_created_records',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='company_department_updated_records',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Department',
                'verbose_name_plural': 'Departments',
                'ordering': ['company__company_name', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Designation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='designations',
                    to='company.company',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='company_designation_created_records',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    editable=False,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='company_designation_updated_records',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Designation',
                'verbose_name_plural': 'Designations',
                'ordering': ['company__company_name', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['code'], name='branch_code_idx'),
        ),
        migrations.AddIndex(
            model_name='department',
            index=models.Index(fields=['code'], name='department_code_idx'),
        ),
        migrations.AddIndex(
            model_name='designation',
            index=models.Index(fields=['code'], name='designation_code_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='department',
            unique_together={('company', 'code')},
        ),
        migrations.AlterUniqueTogether(
            name='designation',
            unique_together={('company', 'code')},
        ),
    ]
