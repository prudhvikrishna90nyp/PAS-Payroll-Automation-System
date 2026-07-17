"""Payroll run locking / immutability (Sprint 8.3)."""

from __future__ import annotations

from apps.payroll.models import PayrollRunStatus
from apps.payroll.services.exceptions import LockedRunError, LockedRunMutationError, RunNotCalculableError
from apps.payroll.services.validation import validate_run_calculable
from apps.payroll.services.workflow import reopen_locked_run, transition_run


def assert_run_mutable(run) -> None:
    """Raise if the run must not be modified (locked / non-calculable for calc)."""
    errors = validate_run_calculable(run)
    if not errors:
        return
    message = errors[0]
    if 'locked' in message.lower():
        raise LockedRunError(message)
    raise RunNotCalculableError(message)


def assert_run_unlocked_for_mutation(run) -> None:
    """Raise if results / components / run data must not be edited or deleted."""
    if run is None:
        return
    status = getattr(run, 'status', None)
    if status == PayrollRunStatus.LOCKED or getattr(run, 'is_locked', False):
        raise LockedRunMutationError(
            'Cannot modify or delete payroll data after the run is locked.'
        )


def lock_run(run, user=None, remarks: str = ''):
    """Approved → Locked; freeze results."""
    return transition_run(
        run,
        PayrollRunStatus.LOCKED,
        user=user,
        remarks=remarks,
    )


def reopen_run(run, user=None, remarks: str = ''):
    """Superuser-only reopen (Locked → Approved) with mandatory reason."""
    return reopen_locked_run(run, user=user, remarks=remarks)
