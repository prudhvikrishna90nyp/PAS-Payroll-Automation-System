"""EPF validation helpers (Sprint 9.1)."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.common.validators import validate_uan
from apps.compliance.models import EmployeePFProfile, PFRuleSet
from apps.compliance.services.pf_engine import resolve_pf_profile


def validate_uan_value(uan: str) -> str:
    """Validate and normalise a UAN (12 digits). Empty allowed."""
    if not uan:
        return ''
    normalized = ''.join(str(uan).split())
    validate_uan(normalized)
    return normalized


def validate_pf_rule_set(rule: PFRuleSet) -> list[str]:
    """Return soft validation messages; raises on hard clean() failures via model."""
    messages: list[str] = []
    try:
        rule.full_clean()
    except ValidationError as exc:
        if hasattr(exc, 'message_dict'):
            for field, errs in exc.message_dict.items():
                for err in errs:
                    messages.append(f'{field}: {err}')
        else:
            messages.extend(exc.messages)
    return messages


def validate_employee_pf_for_payroll(employee, *, require_uan: bool = False) -> list[str]:
    """Pre-calc checks for an employee expected to contribute to PF."""
    errors: list[str] = []
    profile = resolve_pf_profile(employee)

    applicable = True
    if profile is not None:
        applicable = profile.is_pf_applicable
    else:
        applicable = bool(getattr(employee, 'pf_eligible', True))

    if not applicable:
        return errors

    uan = ''
    if profile is not None and profile.uan:
        uan = profile.uan
    elif getattr(employee, 'uan', None):
        uan = employee.uan

    if require_uan and not uan:
        errors.append('Missing UAN for PF-applicable employee.')
    if uan:
        try:
            validate_uan_value(uan)
        except ValidationError as exc:
            errors.extend(exc.messages)

    if profile is not None:
        try:
            profile.full_clean()
        except ValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        errors.append(f'{field}: {err}')
            else:
                errors.extend(exc.messages)

    return errors


def assert_no_duplicate_pf_number(pf_number: str, *, exclude_pk=None) -> None:
    if not pf_number:
        return
    qs = EmployeePFProfile.objects.filter(pf_number=pf_number.strip())
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError('This PF number is already assigned to another employee.')
