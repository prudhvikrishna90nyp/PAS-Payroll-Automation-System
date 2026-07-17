"""Payroll run locking / immutability (Sprint 8.3 scaffold; used by 8.2 calc)."""

from __future__ import annotations

from apps.payroll.services.exceptions import LockedRunError, RunNotCalculableError
from apps.payroll.services.validation import validate_run_calculable


def assert_run_mutable(run) -> None:
    """Raise if the run must not be modified (locked / non-calculable for calc)."""
    errors = validate_run_calculable(run)
    if not errors:
        return
    message = errors[0]
    if 'locked' in message.lower():
        raise LockedRunError(message)
    raise RunNotCalculableError(message)


def lock_run(run, user=None):
    """Approved → Locked; freeze results. Planned for Sprint 8.3."""
    raise NotImplementedError('locking.lock_run is planned for Sprint 8.3')
