"""Payroll engine orchestration (Sprint 8.1 foundation).

Full calculation / approval / locking land in later 8.x sprints.
This module owns period open/close and draft run creation under transactions.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from apps.payroll.models import (
    PayrollPeriod,
    PayrollPeriodStatus,
    PayrollRun,
    PayrollRunStatus,
)
from apps.payroll.services.audit import write_audit_log
from apps.payroll.services.validation import (
    raise_if_errors,
    validate_payroll_period,
    validate_run_creation,
)


@transaction.atomic
def create_period(
    *,
    company,
    month: int,
    year: int,
    start_date,
    end_date,
    user=None,
) -> PayrollPeriod:
    """Create an Open payroll period with uniqueness / overlap checks."""
    period = PayrollPeriod(
        company=company,
        month=month,
        year=year,
        start_date=start_date,
        end_date=end_date,
        status=PayrollPeriodStatus.OPEN,
        created_by=user,
        updated_by=user,
    )
    errors = validate_payroll_period(period)
    raise_if_errors(errors)
    period.save()
    write_audit_log(
        action='period_create',
        user=user,
        period=period,
        details={
            'month': month,
            'year': year,
            'status': period.status,
            'start_date': str(start_date),
            'end_date': str(end_date),
        },
    )
    return period


@transaction.atomic
def open_period(period: PayrollPeriod, user=None) -> PayrollPeriod:
    """Mark a payroll period Open (re-open if previously closed)."""
    previous = period.status
    period.status = PayrollPeriodStatus.OPEN
    update_fields = ['status', 'updated_at']
    if user is not None:
        period.updated_by = user
        update_fields.append('updated_by')
    period.save(update_fields=update_fields)
    write_audit_log(
        action='period_open',
        user=user,
        period=period,
        details={'previous_status': previous, 'status': period.status},
    )
    return period


@transaction.atomic
def close_period(period: PayrollPeriod, user=None) -> PayrollPeriod:
    """Mark a payroll period Closed."""
    if period.status == PayrollPeriodStatus.CLOSED:
        raise ValidationError('Payroll period is already closed.')
    previous = period.status
    period.status = PayrollPeriodStatus.CLOSED
    update_fields = ['status', 'updated_at']
    if user is not None:
        period.updated_by = user
        update_fields.append('updated_by')
    period.save(update_fields=update_fields)
    write_audit_log(
        action='period_close',
        user=user,
        period=period,
        details={'previous_status': previous, 'status': period.status},
    )
    return period


@transaction.atomic
def create_run(
    *,
    period: PayrollPeriod,
    user=None,
    notes: str = '',
    company=None,
) -> PayrollRun:
    """Create a Draft payroll run for an open company period."""
    company = company or period.company
    errors = validate_run_creation(period, company=company)
    raise_if_errors(errors)

    next_number = (
        PayrollRun.objects.filter(period=period).aggregate(m=Max('run_number')).get('m') or 0
    ) + 1

    run = PayrollRun(
        period=period,
        company=company,
        run_number=next_number,
        status=PayrollRunStatus.DRAFT,
        notes=notes or '',
        created_by=user,
    )
    run.full_clean()
    run.save()
    write_audit_log(
        action='run_create',
        user=user,
        period=period,
        run=run,
        details={
            'run_number': run.run_number,
            'status': run.status,
            'company_id': company.pk,
        },
    )
    return run


@transaction.atomic
def process_company_run(run: PayrollRun, user=None) -> PayrollRun:
    """Company-level processing scaffold (calculation lands in 8.2).

    Wrapped in ``transaction.atomic`` so later steps share one unit of work.
    """
    if run.status == PayrollRunStatus.LOCKED:
        raise ValidationError('Cannot process a locked payroll run.')
    # Stub: attendance_loader / salary_loader / earnings / deductions in 8.2+
    write_audit_log(
        action='run_process_scaffold',
        user=user,
        period=run.period,
        run=run,
        details={'status': run.status, 'note': 'Scaffold only; calculation deferred to 8.2'},
    )
    return run
