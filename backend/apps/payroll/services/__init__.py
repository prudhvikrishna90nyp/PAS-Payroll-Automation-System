"""Payroll calculation and generation services."""

from .payslip_generator import (
    calculate_payslip_amounts,
    generate_payslip,
    generate_payslips_for_period,
)
from .salary_calculator import (
    CalculationResult,
    calculate_assignment_components,
    calculate_structure_components,
)
from .formula_engine import FormulaError, evaluate_formula, extract_references
from .validation import SalaryValidationError, validate_structure, validate_component
from .payroll_engine import close_period, create_period, create_run, open_period
from .audit import write_audit_log

__all__ = [
    'CalculationResult',
    'FormulaError',
    'SalaryValidationError',
    'calculate_assignment_components',
    'calculate_payslip_amounts',
    'calculate_structure_components',
    'close_period',
    'create_period',
    'create_run',
    'evaluate_formula',
    'extract_references',
    'generate_payslip',
    'generate_payslips_for_period',
    'open_period',
    'validate_component',
    'validate_structure',
    'write_audit_log',
]
