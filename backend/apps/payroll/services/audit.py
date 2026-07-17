"""Payroll audit log helpers."""

from __future__ import annotations

from typing import Any


def write_audit_log(
    *,
    action: str,
    user=None,
    period=None,
    run=None,
    details: dict[str, Any] | None = None,
):
    """Persist a PayrollAuditLog entry for period/run lifecycle actions."""
    from apps.payroll.models import PayrollAuditLog

    return PayrollAuditLog.objects.create(
        action=action,
        user=user,
        period=period,
        run=run,
        details=details or {},
    )


def write_status_transition_audit(
    *,
    action: str,
    run,
    user=None,
    previous_status: str,
    new_status: str,
    remarks: str = '',
    extra: dict[str, Any] | None = None,
):
    """Audit a run status change with required transition metadata."""
    details: dict[str, Any] = {
        'previous_status': previous_status,
        'new_status': new_status,
        'remarks': (remarks or '').strip(),
        'user_id': getattr(user, 'pk', None),
        'username': getattr(user, 'get_username', lambda: None)() if user else None,
    }
    if extra:
        details.update(extra)
    return write_audit_log(
        action=action,
        user=user,
        period=getattr(run, 'period', None),
        run=run,
        details=details,
    )
