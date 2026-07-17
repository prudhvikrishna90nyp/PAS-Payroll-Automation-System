from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_payroll_engine_foundation_sprint81'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrun',
            name='calculation_errors',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Per-employee calculation errors from the last calculate_run().',
            ),
        ),
        migrations.AlterField(
            model_name='payrollrun',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('calculated', 'Calculated'),
                    ('incomplete', 'Incomplete'),
                    ('reviewed', 'Reviewed'),
                    ('approved', 'Approved'),
                    ('locked', 'Locked'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
    ]
