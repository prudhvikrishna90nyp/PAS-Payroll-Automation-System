from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed_attendance_role_groups(sender, **kwargs):
    from .permissions import seed_role_groups

    seed_role_groups()


class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attendance'
    verbose_name = 'Attendance Management'

    def ready(self):
        post_migrate.connect(_seed_attendance_role_groups, sender=self)
