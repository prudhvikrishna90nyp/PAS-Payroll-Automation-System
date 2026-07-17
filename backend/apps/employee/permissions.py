"""Role groups and permission helpers for employee management."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    'Super Admin': {
        'employee': ('add', 'change', 'delete', 'view'),
        'employeedocument': ('add', 'change', 'delete', 'view'),
        'salarystructure': ('add', 'change', 'delete', 'view'),
    },
    'Admin': {
        'employee': ('add', 'change', 'delete', 'view'),
        'employeedocument': ('add', 'change', 'delete', 'view'),
        'salarystructure': ('add', 'change', 'delete', 'view'),
    },
    'HR': {
        'employee': ('add', 'change', 'view'),
        'employeedocument': ('add', 'change', 'delete', 'view'),
        'salarystructure': ('view',),
    },
    'Payroll': {
        'employee': ('view', 'change'),
        'employeedocument': ('view',),
        'salarystructure': ('view',),
    },
    'Viewer': {
        'employee': ('view',),
        'employeedocument': ('view',),
        'salarystructure': ('view',),
    },
}

VIEW_EMPLOYEE = 'employee.view_employee'
ADD_EMPLOYEE = 'employee.add_employee'
CHANGE_EMPLOYEE = 'employee.change_employee'
DELETE_EMPLOYEE = 'employee.delete_employee'


def seed_role_groups():
    """Merge employee-related permissions into PAS role groups (does not wipe others)."""
    from .models import Employee, EmployeeDocument, SalaryStructure

    model_map = {
        'employee': Employee,
        'employeedocument': EmployeeDocument,
        'salarystructure': SalaryStructure,
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
