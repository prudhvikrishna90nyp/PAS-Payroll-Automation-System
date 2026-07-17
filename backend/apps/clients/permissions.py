"""Role groups and permission helpers for client master."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    'Super Admin': {
        'client': ('add', 'change', 'delete', 'view'),
    },
    'Admin': {
        'client': ('add', 'change', 'delete', 'view'),
    },
    'HR': {
        'client': ('view', 'change'),
    },
    'Payroll': {
        'client': ('view',),
    },
    'Viewer': {
        'client': ('view',),
    },
}

VIEW_CLIENT = 'clients.view_client'
ADD_CLIENT = 'clients.add_client'
CHANGE_CLIENT = 'clients.change_client'
DELETE_CLIENT = 'clients.delete_client'


def seed_role_groups():
    """Merge client permissions into PAS role groups."""
    from .models import Client

    model_map = {'client': Client}
    for group_name, model_perms in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = list(group.permissions.all())
        for model_key, actions in model_perms.items():
            content_type = ContentType.objects.get_for_model(model_map[model_key])
            for action in actions:
                codename = f'{action}_{model_key}'
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                except Permission.DoesNotExist:
                    continue
                if perm not in permissions:
                    permissions.append(perm)
        group.permissions.set(permissions)
    return list(ROLE_GROUPS.keys())
