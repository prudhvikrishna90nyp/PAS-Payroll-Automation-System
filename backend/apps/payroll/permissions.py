"""Role groups and permission helpers for payroll / salary masters."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    'Super Admin': {
        'salarycomponent': ('add', 'change', 'delete', 'view', 'export'),
        'salarystructure': ('add', 'change', 'delete', 'view', 'export'),
        'salarystructureline': ('add', 'change', 'delete', 'view'),
        'employeesalaryassignment': ('add', 'change', 'delete', 'view', 'export'),
        'payslip': ('add', 'change', 'delete', 'view'),
        'payperiod': ('add', 'change', 'delete', 'view'),
    },
    'Admin': {
        'salarycomponent': ('add', 'change', 'delete', 'view', 'export'),
        'salarystructure': ('add', 'change', 'delete', 'view', 'export'),
        'salarystructureline': ('add', 'change', 'delete', 'view'),
        'employeesalaryassignment': ('add', 'change', 'delete', 'view', 'export'),
        'payslip': ('add', 'change', 'delete', 'view'),
        'payperiod': ('add', 'change', 'delete', 'view'),
    },
    'HR': {
        'salarycomponent': ('view',),
        'salarystructure': ('view',),
        'salarystructureline': ('view',),
        'employeesalaryassignment': ('add', 'change', 'view'),
        'payslip': ('view',),
        'payperiod': ('view',),
    },
    'Payroll': {
        'salarycomponent': ('add', 'change', 'view', 'export'),
        'salarystructure': ('add', 'change', 'view', 'export'),
        'salarystructureline': ('add', 'change', 'view'),
        'employeesalaryassignment': ('add', 'change', 'view', 'export'),
        'payslip': ('add', 'change', 'view'),
        'payperiod': ('add', 'change', 'view'),
    },
    'Viewer': {
        'salarycomponent': ('view',),
        'salarystructure': ('view',),
        'salarystructureline': ('view',),
        'employeesalaryassignment': ('view',),
        'payslip': ('view',),
        'payperiod': ('view',),
    },
}

VIEW_COMPONENT = 'payroll.view_salarycomponent'
ADD_COMPONENT = 'payroll.add_salarycomponent'
CHANGE_COMPONENT = 'payroll.change_salarycomponent'
DELETE_COMPONENT = 'payroll.delete_salarycomponent'
EXPORT_COMPONENT = 'payroll.export_salarycomponent'

VIEW_STRUCTURE = 'payroll.view_salarystructure'
ADD_STRUCTURE = 'payroll.add_salarystructure'
CHANGE_STRUCTURE = 'payroll.change_salarystructure'
DELETE_STRUCTURE = 'payroll.delete_salarystructure'
EXPORT_STRUCTURE = 'payroll.export_salarystructure'

VIEW_ASSIGNMENT = 'payroll.view_employeesalaryassignment'
ADD_ASSIGNMENT = 'payroll.add_employeesalaryassignment'
CHANGE_ASSIGNMENT = 'payroll.change_employeesalaryassignment'
DELETE_ASSIGNMENT = 'payroll.delete_employeesalaryassignment'
EXPORT_ASSIGNMENT = 'payroll.export_employeesalaryassignment'

VIEW_PAYSLIP = 'payroll.view_payslip'


def seed_role_groups():
    """Merge payroll permissions into existing PAS role groups."""
    from .models import (
        EmployeeSalaryAssignment,
        PayPeriod,
        Payslip,
        SalaryComponent,
        SalaryStructure,
        SalaryStructureLine,
    )

    model_map = {
        'salarycomponent': SalaryComponent,
        'salarystructure': SalaryStructure,
        'salarystructureline': SalaryStructureLine,
        'employeesalaryassignment': EmployeeSalaryAssignment,
        'payslip': Payslip,
        'payperiod': PayPeriod,
    }

    for group_name, model_perms in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        existing = list(group.permissions.all())
        permissions = list(existing)
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
