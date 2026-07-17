from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0004_alter_employee_employee_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='employment_type',
            field=models.CharField(
                choices=[
                    ('permanent', 'Permanent'),
                    ('contract', 'Contract'),
                    ('temporary', 'Temporary'),
                    ('intern', 'Intern'),
                    ('consultant', 'Consultant'),
                ],
                default='permanent',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='employeedocument',
            name='document_type',
            field=models.CharField(
                choices=[
                    ('aadhaar', 'Aadhaar'),
                    ('pan', 'PAN Card'),
                    ('appointment', 'Appointment Letter'),
                    ('resume', 'Resume'),
                    ('educational', 'Educational Certificates'),
                    ('bank_passbook', 'Bank Passbook'),
                    ('pf_form', 'PF Form'),
                    ('esi_card', 'ESI Card'),
                    ('offer_letter', 'Offer Letter'),
                    ('bank_proof', 'Bank Proof'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=30,
            ),
        ),
    ]
