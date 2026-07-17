"""Calculate component amounts for a salary structure / assignment."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP
from typing import TYPE_CHECKING

from .formula_engine import (
    FormulaError,
    detect_circular_references,
    evaluate_formula,
    extract_references,
    normalize_token,
)

if TYPE_CHECKING:
    from apps.payroll.models import EmployeeSalaryAssignment, SalaryStructure, SalaryStructureLine


@dataclass
class CalculationResult:
    amounts: dict[str, Decimal] = field(default_factory=dict)
    gross: Decimal = Decimal('0.00')
    ctc_monthly: Decimal = Decimal('0.00')
    earnings_total: Decimal = Decimal('0.00')
    deductions_total: Decimal = Decimal('0.00')
    employer_total: Decimal = Decimal('0.00')
    lines: list[dict] = field(default_factory=list)


def apply_rounding(amount: Decimal, rule: str) -> Decimal:
    from apps.payroll.models import RoundingRule

    quant = Decimal('0.01')
    if rule == RoundingRule.NONE:
        return amount.quantize(quant, rounding=ROUND_HALF_UP)
    if rule == RoundingRule.NEAREST:
        return amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP).quantize(quant)
    if rule == RoundingRule.ROUND_UP:
        return amount.quantize(Decimal('1'), rounding=ROUND_CEILING).quantize(quant)
    if rule == RoundingRule.ROUND_DOWN:
        return amount.quantize(Decimal('1'), rounding=ROUND_DOWN).quantize(quant)
    return amount.quantize(quant, rounding=ROUND_HALF_UP)


def _line_specs(structure: SalaryStructure) -> list[dict]:
    from apps.payroll.models import CalculationType

    specs = []
    for line in structure.lines.select_related('component').all():
        component = line.component
        if not component.is_active or component.is_deleted:
            continue
        calc = line.effective_calculation_type
        formula = line.effective_formula
        specs.append({
            'line': line,
            'component': component,
            'code': component.component_code,
            'key': normalize_token(component.component_code),
            'name': component.component_name,
            'component_type': component.component_type,
            'calculation_type': calc,
            'value': line.value,
            'percent': line.percent,
            'formula': formula,
            'include_in_gross': component.include_in_gross,
            'include_in_ctc': component.include_in_ctc,
            'rounding_rule': component.rounding_rule,
            'display_order': line.display_order or component.display_order,
            'is_formula': calc == CalculationType.FORMULA,
        })
    specs.sort(key=lambda s: (s['display_order'], s['code']))
    return specs


def _build_dependency_map(specs: list[dict]) -> dict[str, set[str]]:
    from apps.payroll.models import CalculationType

    dep_map: dict[str, set[str]] = {}
    for spec in specs:
        key = spec['key']
        deps: set[str] = set()
        if spec['calculation_type'] == CalculationType.FORMULA and spec['formula']:
            deps = extract_references(spec['formula']) - {key, 'GROSS', 'CTC'}
        dep_map[key] = deps
    return dep_map


def _resolve_order(specs: list[dict]) -> list[dict]:
    dep_map = _build_dependency_map(specs)
    cycles = detect_circular_references(dep_map)
    if cycles:
        cycle_txt = ' -> '.join(cycles[0])
        raise FormulaError(f'Circular formula reference detected: {cycle_txt}')

    by_key = {s['key']: s for s in specs}
    resolved: list[str] = []
    visiting: set[str] = set()

    def visit(key: str):
        if key in resolved:
            return
        if key in visiting:
            raise FormulaError(f'Circular formula reference involving {key}')
        if key not in by_key:
            return
        visiting.add(key)
        for dep in dep_map.get(key, set()):
            visit(dep)
        visiting.remove(key)
        resolved.append(key)

    for spec in specs:
        visit(spec['key'])
    return [by_key[k] for k in resolved if k in by_key]


def calculate_structure_components(
    structure: SalaryStructure,
    gross_salary: Decimal,
    *,
    ctc: Decimal | None = None,
) -> CalculationResult:
    from apps.payroll.models import CalculationType, ComponentType

    gross_salary = Decimal(gross_salary)
    if gross_salary < 0:
        raise FormulaError('Gross salary cannot be negative')

    specs = _line_specs(structure)
    ordered = _resolve_order(specs)

    values: dict[str, Decimal] = {
        'GROSS': gross_salary,
        'CTC': Decimal(ctc or 0),
    }
    result = CalculationResult(gross=gross_salary)

    for spec in ordered:
        calc = spec['calculation_type']
        amount = Decimal('0.00')
        if calc == CalculationType.FIXED:
            amount = Decimal(spec['value'] or 0)
        elif calc == CalculationType.PERCENTAGE:
            # Percentage of gross by default
            pct = Decimal(spec['percent'] or 0)
            amount = (gross_salary * pct / Decimal('100')).quantize(Decimal('0.01'))
        elif calc == CalculationType.FORMULA:
            amount = evaluate_formula(spec['formula'], values)
        amount = apply_rounding(amount, spec['rounding_rule'])
        values[spec['key']] = amount
        # Also expose original code casing
        values[normalize_token(spec['code'])] = amount
        result.amounts[spec['code']] = amount

        line_row = {
            'component_code': spec['code'],
            'component_name': spec['name'],
            'component_type': spec['component_type'],
            'calculation_type': calc,
            'amount': amount,
            'include_in_gross': spec['include_in_gross'],
            'include_in_ctc': spec['include_in_ctc'],
        }
        result.lines.append(line_row)

        if spec['component_type'] == ComponentType.EARNING:
            result.earnings_total += amount
            if spec['include_in_gross']:
                pass  # earnings already part of gross design
        elif spec['component_type'] == ComponentType.DEDUCTION:
            result.deductions_total += amount
        elif spec['component_type'] == ComponentType.EMPLOYER_CONTRIBUTION:
            result.employer_total += amount

    ctc_monthly = Decimal('0.00')
    for row in result.lines:
        if row['include_in_ctc']:
            if row['component_type'] in (
                ComponentType.EARNING,
                ComponentType.EMPLOYER_CONTRIBUTION,
            ):
                ctc_monthly += row['amount']
    result.ctc_monthly = ctc_monthly.quantize(Decimal('0.01'))
    return result


def calculate_assignment_components(
    assignment: EmployeeSalaryAssignment,
) -> CalculationResult:
    return calculate_structure_components(
        assignment.salary_structure,
        assignment.gross_salary,
        ctc=assignment.ctc,
    )
