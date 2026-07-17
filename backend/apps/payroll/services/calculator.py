"""Per-employee payroll calculation orchestrator (Sprint 8.2).

PRORATION BASIS
---------------
Denominator ``calendar_days``: inclusive day count of the ``PayrollPeriod``
(``end_date - start_date + 1``).

Numerator ``payable_days``:
1. **Eligible days** — calendar days in the period on which the employee is
   on rolls: from ``max(date_of_joining, period.start_date)`` through
   ``min(date_of_exit or period.end_date, period.end_date)``. If the
   employee has not joined by period end (or exited before period start),
   eligible days are 0.
2. **With AttendanceMonthlySummary** for the matching company month/year:
   ``payable_days = present_days + paid_leave_days + weekly_off_days + holiday_days``.
   ``present_days`` already counts each half-day as **0.5**. LOP is excluded
   from that sum. Capped at ``eligible_days``.
3. **Without a summary**: ``payable_days = max(0, eligible_days - lop_days)``
   with ``lop_days`` defaulting to 0 (full eligible attendance assumed).

``proration_factor = payable_days / calendar_days`` (zero when calendar_days is 0).

Earnings (and structure deductions) are evaluated at full monthly rates via
the structure engine, then multiplied by ``proration_factor``. Statutory
PF/ESI/PT/TDS amounts are ``Decimal('0.00')`` placeholders until Sprint 9.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from apps.payroll.models import ComponentType
from apps.payroll.services.attendance_loader import AttendanceSnapshot, load_attendance_for_employee
from apps.payroll.services.deductions import build_deduction_rows
from apps.payroll.services.earnings import build_earning_rows
from apps.payroll.services.exceptions import (
    CircularFormulaError,
    EmployeeCalculationError,
    InvalidFormulaError,
)
from apps.payroll.services.formula_engine import FormulaError
from apps.payroll.services.salary_calculator import calculate_assignment_components
from apps.payroll.services.salary_loader import resolve_assignment_for_period


TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


@dataclass
class EmployeeCalcResult:
    employee: object
    assignment: object
    attendance: AttendanceSnapshot
    calendar_days: Decimal
    eligible_days: Decimal
    payable_days: Decimal
    proration_factor: Decimal
    present_days: Decimal
    absent_days: Decimal
    lop_days: Decimal
    overtime_hours: Decimal
    gross: Decimal
    total_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    ctc_snapshot: Decimal | None
    components: list[dict] = field(default_factory=list)
    calculation_detail: dict = field(default_factory=dict)


def eligible_employees_for_run(run):
    """Active company employees on rolls at any point in the period."""
    from apps.employee.models import Employee, EmploymentStatus

    period = run.period
    return (
        Employee.objects
        .filter(
            company_id=run.company_id,
            is_deleted=False,
            is_active=True,
            employment_status=EmploymentStatus.ACTIVE,
            date_of_joining__lte=period.end_date,
        )
        .filter(
            # Still employed at period start, or exited during/after start
            models_q_exit_ok(period.start_date),
        )
        .order_by('employee_code')
    )


def models_q_exit_ok(period_start):
    from django.db.models import Q

    return Q(date_of_exit__isnull=True) | Q(date_of_exit__gte=period_start)


def calendar_days_in_period(period) -> Decimal:
    days = (period.end_date - period.start_date).days + 1
    return Decimal(max(days, 0))


def eligible_days_for_employee(employee, period) -> Decimal:
    start = max(employee.date_of_joining, period.start_date)
    end = period.end_date
    if employee.date_of_exit:
        end = min(end, employee.date_of_exit)
    if start > end:
        return ZERO
    return Decimal((end - start).days + 1)


def compute_payable_days(
    *,
    eligible_days: Decimal,
    attendance: AttendanceSnapshot,
) -> Decimal:
    if eligible_days <= 0:
        return ZERO
    if attendance.source == 'summary':
        payable = (
            attendance.present_days
            + attendance.paid_leave_days
            + attendance.weekly_off_days
            + attendance.holiday_days
        )
        return max(ZERO, min(payable, eligible_days))
    return max(ZERO, eligible_days - attendance.lop_days)


def compute_proration_factor(payable_days: Decimal, calendar_days: Decimal) -> Decimal:
    if calendar_days <= 0:
        return ZERO
    return (payable_days / calendar_days).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def calculate_employee(
    *,
    employee,
    period,
    assignment=None,
    attendance: AttendanceSnapshot | None = None,
) -> EmployeeCalcResult:
    """Calculate one employee's payroll snapshot inputs (not persisted)."""
    if assignment is None:
        assignment = resolve_assignment_for_period(employee, period)
    if attendance is None:
        attendance = load_attendance_for_employee(employee, period)

    calendar_days = calendar_days_in_period(period)
    eligible_days = eligible_days_for_employee(employee, period)
    payable_days = compute_payable_days(eligible_days=eligible_days, attendance=attendance)
    factor = compute_proration_factor(payable_days, calendar_days)

    try:
        full = calculate_assignment_components(assignment)
    except FormulaError as exc:
        msg = str(exc)
        if 'circular' in msg.lower():
            raise CircularFormulaError(msg, employee=employee) from exc
        raise InvalidFormulaError(msg, employee=employee) from exc

    earning_rows = build_earning_rows(full.lines, factor)
    deduction_rows = build_deduction_rows(full.lines, factor)

    # Sprint 9 placeholders — statutory always zero for engine results.
    statutory_rows = [
        {
            'component_code': 'STAT_PF',
            'component_name': 'PF (placeholder)',
            'component_type': ComponentType.DEDUCTION,
            'amount': ZERO,
            'calculation_detail': {
                'placeholder': True,
                'sprint': 9,
                'note': 'Statutory PF deferred to Sprint 9',
            },
        },
        {
            'component_code': 'STAT_ESI',
            'component_name': 'ESI (placeholder)',
            'component_type': ComponentType.DEDUCTION,
            'amount': ZERO,
            'calculation_detail': {
                'placeholder': True,
                'sprint': 9,
                'note': 'Statutory ESI deferred to Sprint 9',
            },
        },
    ]

    total_earnings = sum((r['amount'] for r in earning_rows), ZERO).quantize(TWO_PLACES)
    structure_deductions = sum((r['amount'] for r in deduction_rows), ZERO).quantize(TWO_PLACES)
    # Statutory placeholders are zero until Sprint 9.
    total_deductions = structure_deductions.quantize(TWO_PLACES)
    gross_earnings = total_earnings
    net = (gross_earnings - total_deductions).quantize(TWO_PLACES)

    components = earning_rows + deduction_rows + statutory_rows
    ctc = assignment.ctc
    if ctc is not None:
        ctc = Decimal(ctc).quantize(TWO_PLACES)

    # Present days for snapshot: from summary, else payable for display
    if attendance.source == 'summary':
        present_days = attendance.present_days
        absent_days = attendance.absent_days
        lop_days = attendance.lop_days
        overtime_hours = attendance.overtime_hours
    else:
        present_days = payable_days
        absent_days = max(ZERO, eligible_days - payable_days)
        lop_days = attendance.lop_days
        overtime_hours = ZERO

    return EmployeeCalcResult(
        employee=employee,
        assignment=assignment,
        attendance=attendance,
        calendar_days=calendar_days,
        eligible_days=eligible_days,
        payable_days=payable_days,
        proration_factor=factor,
        present_days=present_days,
        absent_days=absent_days,
        lop_days=lop_days,
        overtime_hours=overtime_hours,
        gross=gross_earnings,
        total_earnings=total_earnings,
        total_deductions=total_deductions,
        net_salary=net,
        ctc_snapshot=ctc,
        components=components,
        calculation_detail={
            'calendar_days': str(calendar_days),
            'eligible_days': str(eligible_days),
            'payable_days': str(payable_days),
            'proration_factor': str(factor),
            'attendance_source': attendance.source,
            'gross_salary_full': str(assignment.gross_salary),
            'statutory': 'placeholders_zero_until_sprint_9',
        },
    )


def safe_calculate_employee(*, employee, period, assignment=None, attendance=None) -> EmployeeCalcResult:
    """Wrapper that normalizes known failures to EmployeeCalculationError."""
    try:
        return calculate_employee(
            employee=employee,
            period=period,
            assignment=assignment,
            attendance=attendance,
        )
    except EmployeeCalculationError:
        raise
    except FormulaError as exc:
        raise InvalidFormulaError(str(exc), employee=employee) from exc
    except Exception as exc:  # noqa: BLE001 — surface as controlled per-employee error
        raise EmployeeCalculationError(str(exc), employee=employee) from exc
