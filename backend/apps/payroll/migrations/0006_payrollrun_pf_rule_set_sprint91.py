# Sprint 9.1 — snapshot PF rule set on payroll runs

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0001_epf_compliance_sprint91'),
        ('payroll', '0005_payroll_approval_locking_sprint83'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrun',
            name='pf_rule_set',
            field=models.ForeignKey(
                blank=True,
                help_text='PF rule set snapshotted at calculation time (immutable historical rates).',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payroll_runs',
                to='compliance.pfruleset',
            ),
        ),
    ]
