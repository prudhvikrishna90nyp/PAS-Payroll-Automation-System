from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed_payroll_role_groups(sender, **kwargs):
    from .permissions import seed_role_groups

    seed_role_groups()


class PayrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payroll'
    verbose_name = 'Payroll & Salary Structures'

    def ready(self):
        post_migrate.connect(_seed_payroll_role_groups, sender=self)
