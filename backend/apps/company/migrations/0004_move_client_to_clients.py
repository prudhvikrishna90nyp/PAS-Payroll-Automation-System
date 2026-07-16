import django.db.models.deletion
from django.db import migrations, models


def update_client_content_type(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.filter(app_label='company', model='client').update(app_label='clients')


def revert_client_content_type(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.filter(app_label='clients', model='client').update(app_label='company')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('company', '0003_client_branch_hierarchy'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='Client',
                ),
                migrations.AlterField(
                    model_name='company',
                    name='client',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='companies',
                        to='clients.client',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE company_client RENAME TO clients_client;',
                    reverse_sql='ALTER TABLE clients_client RENAME TO company_client;',
                ),
            ],
        ),
        migrations.RunPython(update_client_content_type, revert_client_content_type),
    ]
