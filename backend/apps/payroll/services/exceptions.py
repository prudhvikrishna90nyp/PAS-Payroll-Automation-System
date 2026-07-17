"""Payroll calculation domain exceptions (Sprint 8.2)."""

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
