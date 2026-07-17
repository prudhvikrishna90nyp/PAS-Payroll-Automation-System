"""Payroll calculation and workflow domain exceptions (Sprint 8.2 / 8.3)."""

from __future__ import annotations


class PayrollCalculationError(Exception):
    """Base error for payroll run calculation."""


class LockedRunError(PayrollCalculationError):
    """Raised when calculation is attempted on a locked (or non-mutable) run."""


class RunNotCalculableError(PayrollCalculationError):
    """Raised when run status does not allow calculation/recalculation."""


class EmployeeCalculationError(PayrollCalculationError):
    """Per-employee calculation failure (does not imply silent zero pay)."""

    def __init__(self, message: str, *, employee=None, code: str = 'employee_error'):
        super().__init__(message)
        self.employee = employee
        self.code = code
        self.message = message


class MissingSalaryAssignmentError(EmployeeCalculationError):
    def __init__(self, message: str, *, employee=None):
        super().__init__(message, employee=employee, code='missing_salary_assignment')


class InvalidFormulaError(EmployeeCalculationError):
    def __init__(self, message: str, *, employee=None):
        super().__init__(message, employee=employee, code='invalid_formula')


class CircularFormulaError(EmployeeCalculationError):
    def __init__(self, message: str, *, employee=None):
        super().__init__(message, employee=employee, code='circular_formula')


class PayrollWorkflowError(Exception):
    """Base error for payroll approval / locking workflow."""


class InvalidTransitionError(PayrollWorkflowError):
    """Raised when a status transition is not allowed (skip / wrong source)."""


class RunNotReadyError(PayrollWorkflowError):
    """Raised when review/approve is blocked by errors or incomplete results."""


class LockedRunMutationError(PayrollWorkflowError):
    """Raised when mutating results/components/run after lock."""
