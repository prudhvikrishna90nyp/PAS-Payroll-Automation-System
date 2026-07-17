from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.company.models import Company
from apps.employee.models import Employee

from .models import (
    CalculationType,
    ComponentType,
    EmployeeSalaryAssignment,
    PayPeriod,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)
from .permissions import seed_role_groups
from .seed import seed_standard_components
from .services.formula_engine import (
    FormulaError,
    detect_circular_references,
    evaluate_formula,
    extract_references,
)
from .services.payslip_generator import calculate_payslip_amounts, generate_payslip
from .services.salary_calculator import calculate_structure_components
from .services.validation import validate_component, validate_structure


def _perm(codename):
    return Permission.objects.get(codename=codename, content_type__app_label='payroll')


class PayrollTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='payadmin',
            password='TestPassword123!',
        )
        for codename in (
            'view_salarycomponent',
            'add_salarycomponent',
            'change_salarycomponent',
            'delete_salarycomponent',
            'export_salarycomponent',
            'view_salarystructure',
            'add_salarystructure',
            'change_salarystructure',
            'delete_salarystructure',
            'export_salarystructure',
            'view_salarystructureline',
            'add_salarystructureline',
            'change_salarystructureline',
            'delete_salarystructureline',
            'view_employeesalaryassignment',
            'add_employeesalaryassignment',
            'change_employeesalaryassignment',
            'delete_employeesalaryassignment',
            'export_employeesalaryassignment',
            'view_payslip',
            'add_payslip',
            'change_payslip',
        ):
            try:
                self.user.user_permissions.add(_perm(codename))
            except Permission.DoesNotExist:
                pass

        self.client_record = Client.objects.create(
            client_code='PAYCLI',
            client_name='Payroll Client',
            mobile='9876543210',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='Payroll Co',
        )
        self.employee = Employee.objects.create(
            company=self.company,
            employee_code='EMP7001',
            first_name='Ravi',
            last_name='Kumar',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
        )


class FormulaEngineTests(TestCase):
    def test_basic_percentage_of_gross(self):
        result = evaluate_formula('Gross * 40 / 100', {'GROSS': Decimal('50000')})
        self.assertEqual(result, Decimal('20000.00'))

    def test_hra_of_basic(self):
        result = evaluate_formula(
            'Basic * 40 / 100',
            {'BASIC': Decimal('20000'), 'GROSS': Decimal('50000')},
        )
        self.assertEqual(result, Decimal('8000.00'))

    def test_special_balance_formula(self):
        result = evaluate_formula(
            'Gross - (Basic + HRA)',
            {
                'GROSS': Decimal('50000'),
                'BASIC': Decimal('20000'),
                'HRA': Decimal('8000'),
            },
        )
        self.assertEqual(result, Decimal('22000.00'))

    def test_assignment_style_formula(self):
        result = evaluate_formula('Basic = Gross * 40 / 100', {'GROSS': Decimal('10000')})
        self.assertEqual(result, Decimal('4000.00'))

    def test_rejects_eval_and_calls(self):
        with self.assertRaises(FormulaError):
            evaluate_formula('__import__("os").system("echo hi")', {'GROSS': 1})
        with self.assertRaises(FormulaError):
            evaluate_formula('abs(Gross)', {'GROSS': 10})

    def test_division_by_zero(self):
        with self.assertRaises(FormulaError):
            evaluate_formula('Gross / 0', {'GROSS': 10})

    def test_extract_references(self):
        refs = extract_references('Gross - (Basic + HRA + Conveyance)')
        self.assertIn('GROSS', refs)
        self.assertIn('BASIC', refs)
        self.assertIn('HRA', refs)
        self.assertIn('CONVEYANCE', refs)

    def test_circular_detection(self):
        cycles = detect_circular_references({
            'A': {'B'},
            'B': {'C'},
            'C': {'A'},
        })
        self.assertTrue(cycles)


class SalaryCalculatorTests(PayrollTestMixin, TestCase):
    def _office_structure(self):
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company,
            code='OFFICE',
            name='Office Staff',
        )
        for code, formula, order in (
            ('BASIC', 'Gross * 40 / 100', 10),
            ('HRA', 'Basic * 40 / 100', 20),
            ('CONVEYANCE', None, 30),
            ('SPECIAL', 'Gross - (Basic + HRA + Conveyance)', 40),
        ):
            component = SalaryComponent.objects.get(company=self.company, component_code=code)
            SalaryStructureLine.objects.create(
                structure=structure,
                component=component,
                calculation_type=CalculationType.FORMULA if formula else CalculationType.FIXED,
                formula_override=formula or '',
                value=Decimal('1600.00') if code == 'CONVEYANCE' else None,
                display_order=order,
            )
        return structure

    def test_standard_breakdown(self):
        structure = self._office_structure()
        result = calculate_structure_components(structure, Decimal('50000.00'))
        self.assertEqual(result.amounts['BASIC'], Decimal('20000.00'))
        self.assertEqual(result.amounts['HRA'], Decimal('8000.00'))
        self.assertEqual(result.amounts['CONVEYANCE'], Decimal('1600.00'))
        self.assertEqual(result.amounts['SPECIAL'], Decimal('20400.00'))

    def test_circular_formula_raises(self):
        a = SalaryComponent.objects.create(
            company=self.company,
            component_code='A1',
            component_name='A',
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.FORMULA,
            formula='B1',
        )
        b = SalaryComponent.objects.create(
            company=self.company,
            component_code='B1',
            component_name='B',
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.FORMULA,
            formula='A1',
        )
        structure = SalaryStructure.objects.create(
            company=self.company, code='CIRC', name='Circular'
        )
        SalaryStructureLine.objects.create(structure=structure, component=a, display_order=1)
        SalaryStructureLine.objects.create(structure=structure, component=b, display_order=2)
        with self.assertRaises(FormulaError):
            calculate_structure_components(structure, Decimal('10000'))


class ValidationTests(PayrollTestMixin, TestCase):
    def test_duplicate_component_code(self):
        SalaryComponent.objects.create(
            company=self.company,
            component_code='BASIC',
            component_name='Basic',
            component_type=ComponentType.EARNING,
        )
        dup = SalaryComponent(
            company=self.company,
            component_code='basic',
            component_name='Basic Two',
            component_type=ComponentType.EARNING,
        )
        errors = validate_component(dup)
        self.assertTrue(any('Duplicate component code' in e for e in errors))

    def test_missing_basic_in_structure(self):
        hra = SalaryComponent.objects.create(
            company=self.company,
            component_code='HRA',
            component_name='HRA',
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.FIXED,
        )
        structure = SalaryStructure.objects.create(
            company=self.company, code='NOBASIC', name='No Basic'
        )
        SalaryStructureLine.objects.create(
            structure=structure, component=hra, value=Decimal('1000'), display_order=1
        )
        errors = validate_structure(structure)
        self.assertTrue(any('BASIC' in e for e in errors))


class SeedAndAssignmentTests(PayrollTestMixin, TestCase):
    def test_seed_standard_components_idempotent(self):
        first = seed_standard_components(self.company)
        second = seed_standard_components(self.company)
        self.assertGreaterEqual(len(first), 15)
        self.assertEqual(len(second), 0)
        self.assertTrue(
            SalaryComponent.objects.filter(company=self.company, component_code='BASIC').exists()
        )

    def test_assignment_soft_ends_previous(self):
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company, code='OFF', name='Office'
        )
        basic = SalaryComponent.objects.get(company=self.company, component_code='BASIC')
        SalaryStructureLine.objects.create(
            structure=structure,
            component=basic,
            calculation_type=CalculationType.FORMULA,
            formula_override='Gross * 40 / 100',
            display_order=10,
        )
        first = EmployeeSalaryAssignment.objects.create(
            employee=self.employee,
            salary_structure=structure,
            effective_from=date(2026, 1, 1),
            gross_salary=Decimal('40000.00'),
            ctc=Decimal('480000.00'),
        )
        second = EmployeeSalaryAssignment.objects.create(
            employee=self.employee,
            salary_structure=structure,
            effective_from=date(2026, 7, 1),
            gross_salary=Decimal('50000.00'),
            ctc=Decimal('600000.00'),
        )
        first.refresh_from_db()
        self.assertEqual(first.effective_to, date(2026, 6, 30))
        self.assertIsNone(second.effective_to)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.basic_salary, Decimal('20000.00'))


class PayslipIntegrationTests(PayrollTestMixin, TestCase):
    def test_legacy_payslip_still_works(self):
        period = PayPeriod.objects.create(
            year=2026,
            month=7,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
        gross, deductions, net, earnings, deduction_items = calculate_payslip_amounts(
            self.employee, period
        )
        self.assertGreater(gross, 0)
        self.assertEqual(len(earnings), 3)
        payslip = generate_payslip(self.employee, period)
        self.assertEqual(payslip.employee_id, self.employee.pk)
        self.assertTrue(payslip.items.exists())

    def test_structure_aware_payslip(self):
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company, code='OFF', name='Office'
        )
        for code, formula, value in (
            ('BASIC', 'Gross * 40 / 100', None),
            ('HRA', 'Basic * 40 / 100', None),
            ('CONVEYANCE', None, Decimal('1600')),
        ):
            component = SalaryComponent.objects.get(company=self.company, component_code=code)
            SalaryStructureLine.objects.create(
                structure=structure,
                component=component,
                calculation_type=CalculationType.FORMULA if formula else CalculationType.FIXED,
                formula_override=formula or '',
                value=value,
            )
        EmployeeSalaryAssignment.objects.create(
            employee=self.employee,
            salary_structure=structure,
            effective_from=date(2026, 1, 1),
            gross_salary=Decimal('50000.00'),
            ctc=Decimal('600000.00'),
        )
        period = PayPeriod.objects.create(
            year=2026,
            month=7,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
        payslip = generate_payslip(self.employee, period)
        self.assertEqual(payslip.basic_salary, Decimal('20000.00'))
        self.assertEqual(payslip.gross_pay, Decimal('50000.00'))


class PayrollPermissionViewTests(PayrollTestMixin, TestCase):
    def test_component_list_requires_login(self):
        url = reverse('payroll:component_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_component_list_ok(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payroll:component_list'))
        self.assertEqual(response.status_code, 200)

    def test_structure_list_ok(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payroll:structure_list'))
        self.assertEqual(response.status_code, 200)

    def test_assignment_list_ok(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payroll:assignment_list'))
        self.assertEqual(response.status_code, 200)

    def test_seed_components_view(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('payroll:component_seed'),
            {'company': self.company.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SalaryComponent.objects.filter(company=self.company, component_code='EE_PF').exists()
        )

    def test_component_create(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('payroll:component_add'),
            {
                'company': self.company.pk,
                'component_code': 'TEST',
                'component_name': 'Test Comp',
                'component_type': ComponentType.EARNING,
                'calculation_type': CalculationType.FIXED,
                'formula': '',
                'rounding_rule': 'nearest',
                'display_order': 50,
                'taxable': True,
                'include_in_ctc': True,
                'include_in_gross': True,
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SalaryComponent.objects.filter(company=self.company, component_code='TEST').exists()
        )

    def test_reports_download(self):
        self.client.force_login(self.user)
        seed_standard_components(self.company)
        for report in (
            'component_register',
            'structure_register',
            'employee_salary_register',
            'salary_revision',
            'ctc_register',
        ):
            response = self.client.get(reverse('payroll:report_download', args=[report]))
            self.assertEqual(response.status_code, 200, report)
            self.assertIn(
                'spreadsheetml',
                response['Content-Type'],
            )

    def test_payslip_list_namespaced(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payroll:payslip_list'))
        self.assertEqual(response.status_code, 200)

    def test_seed_role_groups(self):
        names = seed_role_groups()
        self.assertIn('Payroll', names)


class NegativeSalaryValidationTests(PayrollTestMixin, TestCase):
    def test_negative_gross_rejected_by_calculator(self):
        structure = SalaryStructure.objects.create(
            company=self.company, code='X', name='X'
        )
        with self.assertRaises(FormulaError):
            calculate_structure_components(structure, Decimal('-1'))
