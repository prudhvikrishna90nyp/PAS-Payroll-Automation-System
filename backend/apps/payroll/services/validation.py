"""Validation helpers for salary masters and structures."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from .formula_engine import FormulaError, detect_circular_references, extract_references, normalize_token


class SalaryValidationError(ValidationError):
    """Domain validation error for salary masters."""


MANDATORY_COMPONENT_CODES = ('BASIC',)


def validate_component(component, *, company=None) -> list[str]:
    """Return list of validation error messages for a SalaryComponent instance."""
    from apps.payroll.models import CalculationType, SalaryComponent

    errors: list[str] = []
    company = company or component.company
    code = (component.component_code or '').strip().upper()
    name = (component.component_name or '').strip()

    if not code:
        errors.append('Component code is required.')
    if not name:
        errors.append('Component name is required.')

    if company and code:
        qs = SalaryComponent.objects.filter(company=company, component_code__iexact=code)
        if component.pk:
            qs = qs.exclude(pk=component.pk)
        if qs.exists():
            errors.append(f'Duplicate component code "{code}" for this company.')

    if company and name:
        qs = SalaryComponent.objects.filter(company=company, component_name__iexact=name)
        if component.pk:
            qs = qs.exclude(pk=component.pk)
        if qs.exists():
            errors.append(f'Duplicate component name "{name}" for this company.')

    if component.calculation_type == CalculationType.FORMULA and not (component.formula or '').strip():
        errors.append('Formula is required when calculation type is Formula.')

    if component.formula:
        try:
            extract_references(component.formula)
        except FormulaError as exc:
            errors.append(str(exc))

    return errors


def validate_structure(structure) -> list[str]:
    """Validate structure lines: mandatory components, circular formulas, percents."""
    from apps.payroll.models import CalculationType, SalaryStructure

    errors: list[str] = []
    if not isinstance(structure, SalaryStructure):
        return ['Invalid salary structure.']

    lines = list(structure.lines.select_related('component').all())
    if not lines:
        errors.append('Salary structure must have at least one component line.')
        return errors

    codes = {normalize_token(line.component.component_code) for line in lines}
    for mandatory in MANDATORY_COMPONENT_CODES:
        if mandatory not in codes:
            errors.append(f'Missing mandatory component: {mandatory}.')

    dep_map: dict[str, set[str]] = {}
    for line in lines:
        key = normalize_token(line.component.component_code)
        calc = line.effective_calculation_type
        formula = line.effective_formula
        deps: set[str] = set()
        if calc == CalculationType.FORMULA and formula:
            try:
                deps = extract_references(formula) - {key, 'GROSS', 'CTC'}
            except FormulaError as exc:
                errors.append(f'{line.component.component_code}: {exc}')
        if calc == CalculationType.PERCENTAGE:
            if line.percent is None:
                errors.append(f'{line.component.component_code}: percent is required.')
            elif line.percent < 0 or line.percent > 1000:
                errors.append(f'{line.component.component_code}: invalid percentage.')
        if calc == CalculationType.FIXED and line.value is not None and line.value < 0:
            errors.append(f'{line.component.component_code}: value cannot be negative.')
        dep_map[key] = deps

    cycles = detect_circular_references(dep_map)
    for cycle in cycles:
        errors.append('Circular formula reference: ' + ' -> '.join(cycle))

    return errors


def validate_assignment(assignment) -> list[str]:
    """Validate employee salary assignment amounts and dates."""
    errors: list[str] = []
    if assignment.gross_salary is not None and assignment.gross_salary < 0:
        errors.append('Gross salary cannot be negative.')
    if assignment.ctc is not None and assignment.ctc < 0:
        errors.append('CTC cannot be negative.')
    if (
        assignment.employee_id
        and assignment.salary_structure_id
        and assignment.employee.company_id != assignment.salary_structure.company_id
    ):
        errors.append('Salary structure company must match the employee company.')
    if assignment.effective_to and assignment.effective_from:
        if assignment.effective_to < assignment.effective_from:
            errors.append('Effective to cannot be before effective from.')

    # Overlap check for open-ended / overlapping ranges
    if assignment.employee_id and assignment.effective_from:
        from apps.payroll.models import EmployeeSalaryAssignment

        qs = EmployeeSalaryAssignment.objects.filter(employee_id=assignment.employee_id)
        if assignment.pk:
            qs = qs.exclude(pk=assignment.pk)
        start = assignment.effective_from
        end = assignment.effective_to
        for other in qs:
            other_end = other.effective_to
            other_start = other.effective_from
            # ranges overlap if each start <= other end (null end = infinity)
            other_end_ok = other_end is None or other_end >= start
            self_end_ok = end is None or end >= other_start
            if other_end_ok and self_end_ok:
                # Soft-close on save handles open current rows; warn only for hard overlaps
                if other.effective_to is not None or end is not None:
                    errors.append(
                        f'Overlaps existing assignment from {other.effective_from}.'
                    )
                    break

    structure_errors = validate_structure(assignment.salary_structure) if assignment.salary_structure_id else []
    errors.extend(structure_errors)
    return errors


def raise_if_errors(errors: list[str]):
    if errors:
        raise SalaryValidationError(errors)


def validate_payroll_period(period) -> list[str]:
    """Validate PayrollPeriod uniqueness and non-overlapping date ranges."""
    from apps.payroll.models import PayrollPeriod

    errors: list[str] = []
    if period.month is not None and (period.month < 1 or period.month > 12):
        errors.append('Month must be between 1 and 12.')
    if period.start_date and period.end_date and period.start_date > period.end_date:
        errors.append('End date must be on or after start date.')

    if period.company_id and period.month and period.year:
        qs = PayrollPeriod.objects.filter(
            company_id=period.company_id,
            month=period.month,
            year=period.year,
        )
        if period.pk:
            qs = qs.exclude(pk=period.pk)
        if qs.exists():
            errors.append(
                f'A payroll period for {period.month:02d}/{period.year} '
                f'already exists for this company.'
            )

    if period.company_id and period.start_date and period.end_date:
        overlap = (
            PayrollPeriod.objects
            .filter(company_id=period.company_id)
            .filter(start_date__lte=period.end_date, end_date__gte=period.start_date)
        )
        if period.pk:
            overlap = overlap.exclude(pk=period.pk)
        if overlap.exists():
            other = overlap.first()
            errors.append(
                f'Date range overlaps existing period '
                f'{other.month:02d}/{other.year} '
                f'({other.start_date} – {other.end_date}).'
            )
    return errors


def validate_run_creation(period, *, company=None) -> list[str]:
    """Validate that a Draft run may be created for the period."""
    from apps.payroll.models import PayrollPeriodStatus

    errors: list[str] = []
    if period is None:
        return ['Payroll period is required.']
    company = company or period.company
    if period.status != PayrollPeriodStatus.OPEN:
        errors.append('Payroll period must be Open to create a run.')
    if company and period.company_id != company.pk:
        errors.append('Company must match the payroll period company.')
    return errors
