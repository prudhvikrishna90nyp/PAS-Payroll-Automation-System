"""Safe salary formula evaluator — never uses Python eval/exec."""

from __future__ import annotations

import ast
import operator
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable


class FormulaError(ValueError):
    """Raised when a formula cannot be parsed or evaluated safely."""


_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Tokens that look like component codes / names (letters, digits, underscore)
_NAME_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

# Normalize common payroll labels to lookup keys
_ALIAS_MAP = {
    'BASIC': 'BASIC',
    'BASICSALARY': 'BASIC',
    'HRA': 'HRA',
    'HOUSERENTALLOWANCE': 'HRA',
    'GROSS': 'GROSS',
    'GROSSSALARY': 'GROSS',
    'CTC': 'CTC',
    'SPECIAL': 'SPECIAL',
    'SPECIALALLOWANCE': 'SPECIAL',
    'CONVEYANCE': 'CONVEYANCE',
    'TRANSPORT': 'CONVEYANCE',
    'TRANSPORTALLOWANCE': 'CONVEYANCE',
    'MEDICAL': 'MEDICAL',
    'WASHING': 'WASHING',
    'BONUS': 'BONUS',
    'INCENTIVE': 'INCENTIVE',
    'OT': 'OT',
    'OVERTIME': 'OT',
    'ARREARS': 'ARREARS',
}


def normalize_token(name: str) -> str:
    compact = re.sub(r'[^A-Za-z0-9]', '', name).upper()
    return _ALIAS_MAP.get(compact, compact)


def extract_references(formula: str) -> set[str]:
    """Return normalized component/variable names referenced in a formula."""
    if not formula or not formula.strip():
        return set()
    # Replace names with placeholders so we can still parse later
    refs = set()
    for match in _NAME_RE.finditer(formula):
        token = match.group(0)
        if token.upper() in {'AND', 'OR', 'NOT'}:
            raise FormulaError(f'Unsupported keyword: {token}')
        refs.add(normalize_token(token))
    return refs


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FormulaError(f'Invalid numeric value: {value}') from exc


def _eval_node(node: ast.AST, values: dict[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, values)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return _to_decimal(node.value)
        raise FormulaError(f'Unsupported constant: {node.value!r}')
    # ast.Num removed in newer Python; keep getattr for older interpreters
    _ast_num = getattr(ast, 'Num', None)
    if _ast_num is not None and isinstance(node, _ast_num):  # pragma: no cover
        return _to_decimal(node.n)
    if isinstance(node, ast.Name):
        key = normalize_token(node.id)
        if key not in values:
            raise FormulaError(f'Unknown reference: {node.id}')
        return _to_decimal(values[key])
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPS:
            raise FormulaError(f'Unsupported operator: {op_type.__name__}')
        left = _eval_node(node.left, values)
        right = _eval_node(node.right, values)
        if op_type is ast.Div and right == 0:
            raise FormulaError('Division by zero')
        if op_type is ast.Pow and (right < 0 or right > 10):
            raise FormulaError('Exponent out of allowed range')
        result = _BINARY_OPS[op_type](left, right)
        return _to_decimal(result)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise FormulaError(f'Unsupported unary operator: {op_type.__name__}')
        return _to_decimal(_UNARY_OPS[op_type](_eval_node(node.operand, values)))
    if isinstance(node, ast.Call):
        raise FormulaError('Function calls are not allowed in formulas')
    if isinstance(node, (ast.Attribute, ast.Subscript, ast.List, ast.Dict, ast.Tuple)):
        raise FormulaError('Unsupported expression construct')
    raise FormulaError(f'Unsupported expression: {type(node).__name__}')


def prepare_formula(formula: str) -> str:
    """Normalize payroll-style formulas for Python AST parsing."""
    text = formula.strip()
    if not text:
        raise FormulaError('Formula is empty')
    # Allow "Basic = Gross * 40 / 100" by stripping left-hand assignment
    if '=' in text:
        left, right = text.split('=', 1)
        if _NAME_RE.fullmatch(left.strip().replace(' ', '')) or _NAME_RE.fullmatch(
            re.sub(r'\s+', '', left.strip())
        ):
            text = right.strip()
        elif left.strip():
            # Keep only RHS when pattern is "Name = expr"
            if re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*$', left.strip()):
                text = right.strip()
    # Replace spaced names like "Special Allowance" is not supported; use codes.
    return text


def evaluate_formula(formula: str, values: dict[str, Decimal | float | int | str]) -> Decimal:
    """
    Evaluate a salary formula safely.

    Supported: +, -, *, /, %, **, parentheses, numeric literals, named references.
    """
    prepared = prepare_formula(formula)
    normalized_values = {
        normalize_token(key): _to_decimal(val) for key, val in values.items()
    }
    try:
        tree = ast.parse(prepared, mode='eval')
    except SyntaxError as exc:
        raise FormulaError(f'Invalid formula syntax: {formula}') from exc
    result = _eval_node(tree, normalized_values)
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def detect_circular_references(
    dependency_map: dict[str, Iterable[str]],
) -> list[list[str]]:
    """
    Return list of cycles found in dependency_map {component: [deps...]}.
    Keys/deps should already be normalized.
    """
    cycles: list[list[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str):
        if node in visiting:
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dep in dependency_map.get(node, []):
            dfs(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for key in dependency_map:
        dfs(key)
    return cycles
