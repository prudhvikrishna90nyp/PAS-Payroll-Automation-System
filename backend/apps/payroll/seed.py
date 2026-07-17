"""Seed standard Indian salary components for a company."""

from __future__ import annotations

from apps.payroll.models import CalculationType, ComponentType, RoundingRule, SalaryComponent

# (code, name, type, calc, formula, taxable, pf, esi, in_ctc, in_gross, order)
STANDARD_COMPONENTS = [
    ('BASIC', 'Basic Salary', ComponentType.EARNING, CalculationType.FORMULA,
     'Gross * 40 / 100', True, True, True, True, True, 10),
    ('HRA', 'House Rent Allowance', ComponentType.EARNING, CalculationType.FORMULA,
     'Basic * 40 / 100', True, False, True, True, True, 20),
    ('CONVEYANCE', 'Conveyance Allowance', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, True, True, True, 30),
    ('SPECIAL', 'Special Allowance', ComponentType.EARNING, CalculationType.FORMULA,
     'Gross - (Basic + HRA + Conveyance)', True, True, True, True, True, 40),
    ('MEDICAL', 'Medical Allowance', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, False, True, True, 50),
    ('WASHING', 'Washing Allowance', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, False, True, True, 60),
    ('BONUS', 'Bonus', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, False, True, True, 70),
    ('INCENTIVE', 'Incentive', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, False, True, True, 80),
    ('OT', 'Overtime', ComponentType.EARNING, CalculationType.FIXED,
     '', True, False, False, False, True, 90),
    ('ARREARS', 'Arrears', ComponentType.EARNING, CalculationType.FIXED,
     '', True, True, True, False, True, 100),
    # Employee deductions
    ('EE_PF', 'Employee PF', ComponentType.DEDUCTION, CalculationType.FORMULA,
     'Basic * 12 / 100', False, False, False, False, False, 200),
    ('EE_ESI', 'Employee ESI', ComponentType.DEDUCTION, CalculationType.FORMULA,
     'Gross * 0.75 / 100', False, False, False, False, False, 210),
    ('PT', 'Professional Tax', ComponentType.DEDUCTION, CalculationType.FIXED,
     '', False, False, False, False, False, 220),
    ('TDS', 'Income Tax (TDS)', ComponentType.DEDUCTION, CalculationType.FIXED,
     '', False, False, False, False, False, 230),
    ('LOAN', 'Loan Recovery', ComponentType.DEDUCTION, CalculationType.FIXED,
     '', False, False, False, False, False, 240),
    ('ADVANCE', 'Advance Recovery', ComponentType.DEDUCTION, CalculationType.FIXED,
     '', False, False, False, False, False, 250),
    ('OTHER_DED', 'Other Deduction', ComponentType.DEDUCTION, CalculationType.FIXED,
     '', False, False, False, False, False, 260),
    # Employer contributions
    ('ER_PF', 'Employer PF', ComponentType.EMPLOYER_CONTRIBUTION, CalculationType.FORMULA,
     'Basic * 12 / 100', False, False, False, True, False, 300),
    ('ER_ESI', 'Employer ESI', ComponentType.EMPLOYER_CONTRIBUTION, CalculationType.FORMULA,
     'Gross * 3.25 / 100', False, False, False, True, False, 310),
    ('GRATUITY', 'Gratuity Provision', ComponentType.EMPLOYER_CONTRIBUTION, CalculationType.FORMULA,
     'Basic * 4.81 / 100', False, False, False, True, False, 320),
    ('BONUS_PROV', 'Bonus Provision', ComponentType.EMPLOYER_CONTRIBUTION, CalculationType.FIXED,
     '', False, False, False, True, False, 330),
]


def seed_standard_components(company, *, user=None) -> list[SalaryComponent]:
    """Create missing standard components for a company. Idempotent."""
    created = []
    for (
        code, name, ctype, calc, formula, taxable, pf, esi, in_ctc, in_gross, order
    ) in STANDARD_COMPONENTS:
        obj, was_created = SalaryComponent.objects.get_or_create(
            company=company,
            component_code=code,
            defaults={
                'component_name': name,
                'component_type': ctype,
                'calculation_type': calc,
                'formula': formula,
                'taxable': taxable,
                'pf_applicable': pf,
                'esi_applicable': esi,
                'include_in_ctc': in_ctc,
                'include_in_gross': in_gross,
                'rounding_rule': RoundingRule.NEAREST,
                'display_order': order,
                'is_active': True,
                'created_by': user,
                'updated_by': user,
            },
        )
        if was_created:
            created.append(obj)
    return created
