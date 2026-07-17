"""EPF / ESI validation helpers (Sprint 9.1 / 9.2)."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.common.validators import validate_esi_ip, validate_uan
from apps.compliance.models import EmployeeESIProfile, EmployeePFProfile, ESIRuleSet, PFRuleSet
from apps.compliance.services.esi_engine import resolve_esi_profile, resolve_ip_number
from apps.compliance.services.pf_engine import resolve_pf_profile


def validate_uan_value(uan: str) -> str:
    """Validate and normalise a UAN (12 digits). Empty allowed."""
    if not uan:
        return ''
    normalized = ''.join(str(uan).split())
    validate_uan(normalized)
    return normalized


def validate_esi_ip_value(ip_number: str) -> str:
    """Validate and normalise an ESI IP number. Empty allowed."""
    if not ip_number:
        return ''
    normalized = ''.join(str(ip_number).split())
    validate_esi_ip(normalized)
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


def validate_esi_rule_set(rule: ESIRuleSet) -> list[str]:
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


def validate_employee_esi_for_payroll(employee, *, require_ip: bool = False) -> list[str]:
    """Pre-calc checks for an employee expected to contribute to ESI."""
    errors: list[str] = []
    profile = resolve_esi_profile(employee)

    applicable = True
    if profile is not None:
        applicable = profile.is_esi_applicable
    else:
        applicable = bool(getattr(employee, 'esi_eligible', False))

    if not applicable:
        return errors

    ip = resolve_ip_number(employee)
    if require_ip and not ip:
        errors.append('Missing ESI IP number for ESI-applicable employee.')
    if ip:
        try:
            validate_esi_ip_value(ip)
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


def assert_no_duplicate_esi_ip(ip_number: str, *, exclude_pk=None) -> None:
    if not ip_number:
        return
    qs = EmployeeESIProfile.objects.filter(ip_number=''.join(ip_number.split()))
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError('This ESI IP number is already assigned to another employee.')
