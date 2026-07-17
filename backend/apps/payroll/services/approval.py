"""Payroll run review and approval (Sprint 8.3)."""

from __future__ import annotations

from apps.payroll.models import PayrollRunStatus
from apps.payroll.services.workflow import transition_run


def mark_reviewed(run, user=None, remarks: str = ''):
    """Calculated → Reviewed."""
    return transition_run(
        run,
        PayrollRunStatus.REVIEWED,
        user=user,
        remarks=remarks,
    )


def submit_for_review(run, user=None, remarks: str = ''):
    """Alias for ``mark_reviewed`` (Calculated → Reviewed)."""
    return mark_reviewed(run, user=user, remarks=remarks)


def approve_run(run, user=None, remarks: str = ''):
    """Reviewed → Approved."""
    return transition_run(
        run,
        PayrollRunStatus.APPROVED,
        user=user,
        remarks=remarks,
    )
