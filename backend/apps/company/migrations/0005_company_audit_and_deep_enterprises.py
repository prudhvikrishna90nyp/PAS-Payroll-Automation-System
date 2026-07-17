import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


COMPANY_COPY_FIELDS = (
    'trade_name',
    'pan',
    'gstin',
    'tan',
    'epf_code',
    'esi_code',
    'professional_tax_registration',
    'labour_licence',
    'address',
    'state',
    'district',
    'pin_code',
    'contact_person',
    'phone',
    'email',
    'bank_details',
    'logo',
)


def _merge_company_fields(target, source):
    updated_fields = []
    for field in COMPANY_COPY_FIELDS:
        target_value = getattr(target, field)
        source_value = getattr(source, field)
        if not target_value and source_value:
            setattr(target, field, source_value)
            updated_fields.append(field)
    if updated_fields:
        target.save(update_fields=updated_fields)


def migrate_deep_enterprises_company(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Company = apps.get_model('company', 'Company')

    deep_client = Client.objects.filter(client_code='CLI001').first()
    if not deep_client:
        deep_client = Client.objects.filter(client_name__iexact='Deep Enterprises').first()
    if not deep_client:
        return

    Company.objects.filter(client__isnull=True).update(client=deep_client)

    deep_companies = list(
        Company.objects.filter(company_name__iexact='Deep Enterprises').order_by('-updated_at')
    )

    target = Company.objects.filter(
        client=deep_client,
        company_name__iexact='Deep Enterprises',
    ).first()

    if not target and deep_companies:
        target = deep_companies[0]
        target.client = deep_client
        target.save(update_fields=['client'])

    if target:
        for duplicate in deep_companies:
            if duplicate.pk == target.pk:
                continue
            _merge_company_fields(target, duplicate)
            duplicate.is_active = False
            duplicate.save(update_fields=['is_active'])
    else:
        Company.objects.create(
            client=deep_client,
            company_name=deep_client.client_name,
            trade_name=deep_client.trade_name or '',
            pan=deep_client.pan or '',
            gstin=deep_client.gstin or '',
            address=deep_client.address_line_1 or '',
            state=deep_client.state or '',
            district=deep_client.district or '',
            pin_code=deep_client.pincode or '',
            contact_person=deep_client.contact_person or '',
            phone=deep_client.mobile or '',
            email=deep_client.email or '',
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_alter_client_alternate_mobile_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('company', '0004_move_client_to_clients'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='company_company_created_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='company_company_updated_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['company_name'], name='company_name_idx'),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['pan'], name='company_pan_idx'),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['gstin'], name='company_gstin_idx'),
        ),
        migrations.RunPython(
            migrate_deep_enterprises_company,
            migrations.RunPython.noop,
        ),
    ]
