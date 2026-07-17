"""Payroll run locking / immutability (stub — Sprint 8.3)."""

from __future__ import annotations


def lock_run(run, user=None):
    """Approved → Locked; freeze results. Planned for Sprint 8.3."""
    raise NotImplementedError('locking.lock_run is planned for Sprint 8.3')


def assert_run_mutable(run):
    """Raise if the run is locked and mutations are not allowed."""
    raise NotImplementedError('locking.assert_run_mutable is planned for Sprint 8.3')
