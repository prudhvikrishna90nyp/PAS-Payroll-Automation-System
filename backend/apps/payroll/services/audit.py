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
