import django.db.models.deletion
from django.db import migrations, models


def assign_default_client(apps, schema_editor):
    Client = apps.get_model('company', 'Client')
    Company = apps.get_model('company', 'Company')

    default_client, _ = Client.objects.get_or_create(
        code='DEFAULT',
        defaults={
            'name': 'Default Client',
            'is_active': True,
        },
    )

    Company.objects.filter(client__isnull=True).update(client=default_client)


def create_head_office_branches(apps, schema_editor):
    Company = apps.get_model('company', 'Company')
    Branch = apps.get_model('company', 'Branch')

    for company in Company.objects.all():
        if company.address or company.state:
            Branch.objects.get_or_create(
                company=company,
                code='HO',
                defaults={
                    'branch_name': 'Head Office',
                    'address': company.address,
                    'state': company.state,
                    'district': company.district,
                    'pin_code': company.pin_code,
                    'contact_person': company.contact_person,
                    'phone': company.phone,
                    'email': company.email,
                    'is_head_office': True,
                    'is_active': company.is_active,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0002_rename_pf_esi_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('contact_person', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='company',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='company',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='company',
            name='client',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='companies',
                to='company.client',
            ),
        ),
        migrations.RunPython(assign_default_client, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='company',
            name='client',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='companies',
                to='company.client',
            ),
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('branch_name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=20)),
                ('address', models.TextField(blank=True)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('district', models.CharField(blank=True, max_length=100)),
                ('pin_code', models.CharField(blank=True, max_length=10, verbose_name='PIN Code')),
                ('contact_person', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_head_office', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='branches',
                    to='company.company',
                )),
            ],
            options={
                'verbose_name_plural': 'Branches',
                'ordering': ['company__company_name', 'branch_name'],
                'unique_together': {('company', 'code')},
            },
        ),
        migrations.RunPython(create_head_office_branches, migrations.RunPython.noop),
    ]
