from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0003_rebuild_employee_master'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='employee_code',
            field=models.CharField(blank=True, max_length=20, verbose_name='Employee Code'),
        ),
    ]
