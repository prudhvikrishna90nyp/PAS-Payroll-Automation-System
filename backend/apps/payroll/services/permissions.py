"""Who may review / approve / lock payroll runs (Sprint 8.3)."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

# Map workflow actions to existing PAS role groups where possible.
REVIEW_GROUPS = frozenset({'HR', 'Payroll', 'Admin', 'Super Admin'})
APPROVE_GROUPS = frozenset({'Admin', 'Super Admin'})
LOCK_GROUPS = frozenset({'Admin', 'Super Admin'})

PERM_REVIEW = 'payroll.review_payrollrun'
PERM_APPROVE = 'payroll.approve_payrollrun'
PERM_LOCK = 'payroll.lock_payrollrun'


def _in_groups(user, group_names: frozenset[str]) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.groups.filter(name__in=group_names).exists()


def can_review_run(user) -> bool:
    """HR / Payroll / Admin may mark a run Reviewed."""
    if user is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user.has_perm(PERM_REVIEW):
        return True
    return _in_groups(user, REVIEW_GROUPS)


def can_approve_run(user) -> bool:
    """Admin / Super Admin may approve a reviewed run."""
    if user is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user.has_perm(PERM_APPROVE):
        return True
    return _in_groups(user, APPROVE_GROUPS)


def can_lock_run(user) -> bool:
    """Admin / Super Admin may lock an approved run."""
    if user is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if user.has_perm(PERM_LOCK):
        return True
    return _in_groups(user, LOCK_GROUPS)


def can_reopen_locked_run(user) -> bool:
    """Reopen is superuser-only (mandatory reason enforced in workflow)."""
    return bool(user is not None and getattr(user, 'is_superuser', False))


def assert_can_review(user) -> None:
    if not can_review_run(user):
        raise PermissionDenied('You do not have permission to review payroll runs.')


def assert_can_approve(user) -> None:
    if not can_approve_run(user):
        raise PermissionDenied('You do not have permission to approve payroll runs.')


def assert_can_lock(user) -> None:
    if not can_lock_run(user):
        raise PermissionDenied('You do not have permission to lock payroll runs.')


def assert_can_reopen(user) -> None:
    if not can_reopen_locked_run(user):
        raise PermissionDenied(
            'Only a superuser may reopen a locked payroll run.'
        )
