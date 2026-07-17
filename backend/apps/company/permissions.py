"""Role groups and permission helpers for company / organisation masters."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    'Super Admin': {
        'company': ('add', 'change', 'delete', 'view'),
        'branch': ('add', 'change', 'delete', 'view'),
        'department': ('add', 'change', 'delete', 'view'),
        'designation': ('add', 'change', 'delete', 'view'),
    },
    'Admin': {
        'company': ('add', 'change', 'delete', 'view'),
        'branch': ('add', 'change', 'delete', 'view'),
        'department': ('add', 'change', 'delete', 'view'),
        'designation': ('add', 'change', 'delete', 'view'),
    },
    'HR': {
        'company': ('view', 'change'),
        'branch': ('add', 'change', 'view'),
        'department': ('add', 'change', 'view'),
        'designation': ('add', 'change', 'view'),
    },
    'Payroll': {
        'company': ('view',),
        'branch': ('view',),
        'department': ('view',),
        'designation': ('view',),
    },
    'Viewer': {
        'company': ('view',),
        'branch': ('view',),
        'department': ('view',),
        'designation': ('view',),
    },
}

VIEW_COMPANY = 'company.view_company'
ADD_COMPANY = 'company.add_company'
CHANGE_COMPANY = 'company.change_company'
DELETE_COMPANY = 'company.delete_company'

VIEW_BRANCH = 'company.view_branch'
ADD_BRANCH = 'company.add_branch'
CHANGE_BRANCH = 'company.change_branch'
DELETE_BRANCH = 'company.delete_branch'

VIEW_DEPARTMENT = 'company.view_department'
ADD_DEPARTMENT = 'company.add_department'
CHANGE_DEPARTMENT = 'company.change_department'
DELETE_DEPARTMENT = 'company.delete_department'

VIEW_DESIGNATION = 'company.view_designation'
ADD_DESIGNATION = 'company.add_designation'
CHANGE_DESIGNATION = 'company.change_designation'
DELETE_DESIGNATION = 'company.delete_designation'


def seed_role_groups():
    """Merge company / organisation permissions into PAS role groups."""
    from .models import Branch, Company, Department, Designation

    model_map = {
        'company': Company,
        'branch': Branch,
        'department': Department,
        'designation': Designation,
    }
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
