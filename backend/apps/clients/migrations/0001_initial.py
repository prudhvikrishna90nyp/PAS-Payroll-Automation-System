import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('company', '0003_client_branch_hierarchy'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Client',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('is_active', models.BooleanField(default=True)),
                        ('is_deleted', models.BooleanField(default=False)),
                        ('deleted_at', models.DateTimeField(blank=True, null=True)),
                        ('name', models.CharField(max_length=200)),
                        ('code', models.CharField(max_length=20, unique=True)),
                        ('contact_person', models.CharField(blank=True, max_length=100)),
                        ('phone', models.CharField(blank=True, max_length=20)),
                        ('email', models.EmailField(blank=True, max_length=254)),
                        ('address', models.TextField(blank=True)),
                    ],
                    options={
                        'ordering': ['name'],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
