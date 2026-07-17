"""Payroll run status transition orchestration (Sprint 8.3)."""

from __future__ import annotations

from django.db import transaction

from apps.payroll.models import PayrollRun, PayrollRunStatus
from apps.payroll.services.audit import write_status_transition_audit
from apps.payroll.services.exceptions import InvalidTransitionError, RunNotReadyError
from apps.payroll.services.permissions import (
    assert_can_approve,
    assert_can_lock,
    assert_can_reopen,
    assert_can_review,
)

# Forward transitions only (reopen handled separately).
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PayrollRunStatus.CALCULATED: {PayrollRunStatus.REVIEWED},
    PayrollRunStatus.REVIEWED: {PayrollRunStatus.APPROVED},
    PayrollRunStatus.APPROVED: {PayrollRunStatus.LOCKED},
}

ACTION_FOR_TARGET = {
    PayrollRunStatus.REVIEWED: 'run_review',
    PayrollRunStatus.APPROVED: 'run_approve',
    PayrollRunStatus.LOCKED: 'run_lock',
}

# Statuses that require a clean calculation before review/approve.
READY_CHECK_TARGETS = {
    PayrollRunStatus.REVIEWED,
    PayrollRunStatus.APPROVED,
}


def _validate_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f'Cannot transition payroll run from "{current}" to "{target}". '
            'Allowed path: Calculated → Reviewed → Approved → Locked.'
        )


def _assert_run_ready_for_advancement(run: PayrollRun, target: str) -> None:
    """Block review/approve when calculation is incomplete or has errors."""
    if target not in READY_CHECK_TARGETS:
        return

    if run.status == PayrollRunStatus.INCOMPLETE:
        raise RunNotReadyError(
            'Cannot advance a run with Incomplete status. Fix errors and recalculate.'
        )
    if run.calculation_errors:
        raise RunNotReadyError(
            'Cannot advance a run that has calculation errors. '
            'Fix errors and recalculate first.'
        )
    result_count = run.results.count()
    if result_count == 0:
        raise RunNotReadyError(
            'Cannot advance a run with no employee results.'
        )


def transition_run(
    run: PayrollRun,
    target_status: str,
    *,
    user=None,
    remarks: str = '',
) -> PayrollRun:
    """Apply a single allowed status transition under row lock + atomic + audit.

    Uses ``select_for_update`` for concurrent transition protection.
    """
    target_status = str(target_status)

    if target_status == PayrollRunStatus.REVIEWED:
        assert_can_review(user)
    elif target_status == PayrollRunStatus.APPROVED:
        assert_can_approve(user)
    elif target_status == PayrollRunStatus.LOCKED:
        assert_can_lock(user)
    else:
        raise InvalidTransitionError(f'Unsupported target status "{target_status}".')

    with transaction.atomic():
        locked = (
            PayrollRun.objects.select_for_update()
            .select_related('period', 'company')
            .get(pk=run.pk)
        )
        previous = locked.status
        if previous == target_status:
            raise InvalidTransitionError(
                f'Payroll run is already "{locked.get_status_display()}".'
            )
        _validate_transition(previous, target_status)
        _assert_run_ready_for_advancement(locked, target_status)

        locked.status = target_status
        locked.save(update_fields=['status', 'updated_at'])

        action = ACTION_FOR_TARGET[target_status]
        write_status_transition_audit(
            action=action,
            run=locked,
            user=user,
            previous_status=previous,
            new_status=target_status,
            remarks=remarks,
        )
        return locked


def reopen_locked_run(
    run: PayrollRun,
    *,
    user=None,
    remarks: str = '',
) -> PayrollRun:
    """Superuser-only: Locked → Calculated with mandatory remarks and full audit.

    Non-superusers are always denied. Returning to Calculated allows
    recalculation and a fresh review → approve → lock cycle.
    """
    assert_can_reopen(user)
    remarks = (remarks or '').strip()
    if not remarks:
        raise InvalidTransitionError(
            'A reason is required to reopen a locked payroll run.'
        )

    with transaction.atomic():
        locked = (
            PayrollRun.objects.select_for_update()
            .select_related('period', 'company')
            .get(pk=run.pk)
        )
        previous = locked.status
        if previous != PayrollRunStatus.LOCKED:
            raise InvalidTransitionError(
                'Only a Locked payroll run can be reopened.'
            )
        locked.status = PayrollRunStatus.CALCULATED
        locked.save(update_fields=['status', 'updated_at'])
        write_status_transition_audit(
            action='run_reopen',
            run=locked,
            user=user,
            previous_status=previous,
            new_status=PayrollRunStatus.CALCULATED,
            remarks=remarks,
            extra={'reopened_by_superuser': True},
        )
        return locked
