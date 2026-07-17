"""Snapshot helpers for payroll results (stub — Sprint 8.2)."""

from __future__ import annotations


def snapshot_employee_result(run, employee, amounts, attendance, ctc=None):
    """Persist PayrollResult + PayrollResultComponent rows for one employee.

    Planned: called from payroll_engine after earnings/deductions.
    """
    raise NotImplementedError('snapshot.snapshot_employee_result is planned for Sprint 8.2')
