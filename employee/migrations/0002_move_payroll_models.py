from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='PayslipItem'),
                migrations.DeleteModel(name='Payslip'),
                migrations.DeleteModel(name='PayPeriod'),
            ],
        ),
    ]
