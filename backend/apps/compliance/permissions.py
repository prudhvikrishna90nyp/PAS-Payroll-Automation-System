"""Role groups and permission helpers for compliance exports."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# Custom export codenames keyed by ContentType model class.
ROLE_GROUPS = {
    'Super Admin': {
        'pfruleset': ('export_pfregister', 'export_ecr'),
        'esiruleset': ('export_esiregister', 'export_esicontribution'),
        'professionaltaxruleset': ('export_ptregister', 'export_ptchallan'),
        'financialyeartaxrule': ('export_tdsregister', 'export_form16'),
    },
    'Admin': {
        'pfruleset': ('export_pfregister', 'export_ecr'),
        'esiruleset': ('export_esiregister', 'export_esicontribution'),
        'professionaltaxruleset': ('export_ptregister', 'export_ptchallan'),
        'financialyeartaxrule': ('export_tdsregister', 'export_form16'),
    },
    'Payroll': {
        'pfruleset': ('export_pfregister', 'export_ecr'),
        'esiruleset': ('export_esiregister', 'export_esicontribution'),
        'professionaltaxruleset': ('export_ptregister', 'export_ptchallan'),
        'financialyeartaxrule': ('export_tdsregister', 'export_form16'),
    },
    'HR': {
        'pfruleset': ('export_pfregister',),
        'esiruleset': ('export_esiregister',),
        'professionaltaxruleset': ('export_ptregister',),
        'financialyeartaxrule': ('export_tdsregister',),
    },
}


def seed_role_groups():
    """Merge compliance export permissions into PAS role groups."""
    from .models import (
        ESIRuleSet,
        FinancialYearTaxRule,
        PFRuleSet,
        ProfessionalTaxRuleSet,
    )

    model_map = {
        'pfruleset': PFRuleSet,
        'esiruleset': ESIRuleSet,
        'professionaltaxruleset': ProfessionalTaxRuleSet,
        'financialyeartaxrule': FinancialYearTaxRule,
    }

    for group_name, model_perms in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = list(group.permissions.all())
        for model_key, codenames in model_perms.items():
            content_type = ContentType.objects.get_for_model(model_map[model_key])
            for codename in codenames:
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                except Permission.DoesNotExist:
                    continue
                if perm not in permissions:
                    permissions.append(perm)
        group.permissions.set(permissions)
    return list(ROLE_GROUPS.keys())
