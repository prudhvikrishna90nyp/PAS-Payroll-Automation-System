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
from .payroll_engine import (
    calculate_run,
    close_period,
    create_period,
    create_run,
    open_period,
    process_company_run,
)
from .audit import write_audit_log, write_status_transition_audit
from .approval import approve_run, mark_reviewed, submit_for_review
from .locking import assert_run_mutable, assert_run_unlocked_for_mutation, lock_run, reopen_run
from .workflow import reopen_locked_run, transition_run

__all__ = [
    'CalculationResult',
    'FormulaError',
    'SalaryValidationError',
    'approve_run',
    'assert_run_mutable',
    'assert_run_unlocked_for_mutation',
    'calculate_assignment_components',
    'calculate_payslip_amounts',
    'calculate_run',
    'calculate_structure_components',
    'close_period',
    'create_period',
    'create_run',
    'evaluate_formula',
    'extract_references',
    'generate_payslip',
    'generate_payslips_for_period',
    'lock_run',
    'mark_reviewed',
    'open_period',
    'process_company_run',
    'reopen_locked_run',
    'reopen_run',
    'submit_for_review',
    'transition_run',
    'validate_component',
    'validate_structure',
    'write_audit_log',
    'write_status_transition_audit',
]
