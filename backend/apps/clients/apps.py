from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.clients'
    verbose_name = 'Clients'

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(_seed_role_groups, sender=self)


def _seed_role_groups(sender, **kwargs):
    from .permissions import seed_role_groups

    seed_role_groups()
