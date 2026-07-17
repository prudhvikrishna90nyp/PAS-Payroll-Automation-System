import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_copy_client_fields(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')

    for client in Client.objects.all():
        client.client_code = (client.code or f'CLI{client.pk:03d}').strip().upper()
        client.client_name = (client.name or 'Unnamed Client').strip()
        client.contact_person = client.contact_person or ''
        client.email = client.email or ''

        phone = (client.phone or '').strip()
        if len(phone) == 10 and phone[0] in '6789':
            client.mobile = phone
        else:
            client.mobile = '9000000000'

        client.address_line_1 = (client.address or 'Address not provided').strip()
        client.city = 'Unknown'
        client.state = 'Unknown'
        client.pincode = '110001'
        client.save()


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('company', '0004_move_client_to_clients'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='address_line_1',
            field=models.CharField(default='Address not provided', max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='address_line_2',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='client',
            name='alternate_mobile',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='client',
            name='city',
            field=models.CharField(default='Unknown', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='client_code',
            field=models.CharField(default='TEMP', max_length=20, unique=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='client_name',
            field=models.CharField(default='Unnamed Client', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='clients_client_created_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='district',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='client',
            name='gstin',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='client',
            name='mobile',
            field=models.CharField(default='9000000000', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='client',
            name='pan',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='client',
            name='pincode',
            field=models.CharField(default='110001', max_length=6),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='state',
            field=models.CharField(default='Unknown', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='trade_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='client',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='clients_client_updated_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(forwards_copy_client_fields, migrations.RunPython.noop),
        migrations.RemoveField(model_name='client', name='address'),
        migrations.RemoveField(model_name='client', name='code'),
        migrations.RemoveField(model_name='client', name='deleted_at'),
        migrations.RemoveField(model_name='client', name='is_deleted'),
        migrations.RemoveField(model_name='client', name='name'),
        migrations.RemoveField(model_name='client', name='phone'),
        migrations.AlterField(
            model_name='client',
            name='client_code',
            field=models.CharField(help_text='Example: CLI001', max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='contact_person',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterModelOptions(
            name='client',
            options={
                'ordering': ['client_name'],
                'verbose_name': 'Client',
                'verbose_name_plural': 'Clients',
            },
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['client_name'], name='client_name_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['client_code'], name='client_code_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['gstin'], name='client_gstin_idx'),
        ),
    ]
