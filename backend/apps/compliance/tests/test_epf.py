"""Sprint 9.1 EPF compliance tests."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.common.validators import validate_uan
from apps.company.models import Company
from apps.compliance.models import EmployeePFProfile, PayrollPFResult, PFRuleSet
from apps.compliance.services.ecr_export import build_ecr_text, iter_ecr_rows
from apps.compliance.services.pf_engine import calculate_pf, determine_pf_wages_from_components
from apps.compliance.services.pf_rules import get_pf_rule_for_date, seed_default_pf_rule_set
from apps.compliance.services.validator import validate_employee_pf_for_payroll, validate_uan_value
from apps.employee.models import Employee
from apps.payroll.models import (
    CalculationType,
    EmployeeSalaryAssignment,
    PayrollResult,
    PayrollRunStatus,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)
from apps.payroll.seed import seed_standard_components
from apps.payroll.services.payroll_engine import calculate_run, create_period, create_run


class ComplianceTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='epfadmin',
            password='TestPassword123!',
            is_staff=True,
        )
        for codename in (
            'view_payrollrun',
            'export_pfregister',
            'export_ecr',
        ):
            try:
                perm = Permission.objects.get(codename=codename)
                self.user.user_permissions.add(perm)
            except Permission.DoesNotExist:
                pass

        self.client_record = Client.objects.create(
            client_code='EPFCLI',
            client_name='EPF Client',
            mobile='9876543210',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='EPF Co',
        )
        self.employee = Employee.objects.create(
            company=self.company,
            employee_code='EPF1001',
            first_name='Sita',
            last_name='Rao',
            date_of_joining=date(2024, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
            pf_eligible=True,
            uan='123456789012',
        )
        self.rule = seed_default_pf_rule_set()


class PFRuleResolutionTests(ComplianceTestMixin, TestCase):
    def test_seed_default_rates(self):
        self.assertEqual(self.rule.pf_wage_ceiling, Decimal('15000.00'))
        self.assertEqual(self.rule.employee_pf_rate, Decimal('0.1200'))
        self.assertEqual(self.rule.eps_rate, Decimal('0.0833'))

    def test_effective_date_resolution(self):
        resolved = get_pf_rule_for_date(date(2026, 7, 31))
        self.assertEqual(resolved.code, self.rule.code)

    def test_no_rule_before_effective(self):
        with self.assertRaises(ValidationError):
            get_pf_rule_for_date(date(2020, 1, 1))

    def test_overlapping_active_rules_rejected(self):
        with self.assertRaises(ValidationError):
            PFRuleSet.objects.create(
                code='IN-EPF-OVERLAP',
                name='Overlap',
                effective_from=date(2024, 6, 1),
                effective_to=None,
                is_active=True,
            )


class PFEngineCalculationTests(ComplianceTestMixin, TestCase):
    def _period(self):
        return type('P', (), {
            'start_date': date(2026, 7, 1),
            'end_date': date(2026, 7, 31),
        })()

    def test_below_ceiling(self):
        rows = [{'component_code': 'BASIC', 'amount': Decimal('10000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertEqual(pf.pf_wages, Decimal('10000.00'))
        self.assertEqual(pf.employee_pf, Decimal('1200.00'))
        self.assertEqual(pf.employer_pf, Decimal('1200.00'))
        self.assertEqual(pf.eps, Decimal('833.00'))
        self.assertEqual(pf.epf, Decimal('367.00'))

    def test_above_ceiling(self):
        rows = [{'component_code': 'BASIC', 'amount': Decimal('25000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertEqual(pf.actual_pf_wages, Decimal('25000.00'))
        self.assertEqual(pf.pf_wages, Decimal('15000.00'))
        self.assertEqual(pf.employee_pf, Decimal('1800.00'))
        self.assertEqual(pf.eps, Decimal('1249.50'))
        self.assertEqual(pf.epf, Decimal('550.50'))

    def test_higher_pension_eps_uncapped(self):
        EmployeePFProfile.objects.create(
            employee=self.employee,
            uan='123456789012',
            is_pf_applicable=True,
            higher_pension=True,
        )
        rows = [{'component_code': 'BASIC', 'amount': Decimal('25000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertEqual(pf.pf_wages, Decimal('25000.00'))
        self.assertEqual(pf.employee_pf, Decimal('3000.00'))
        self.assertEqual(pf.employer_pf, Decimal('3000.00'))
        self.assertEqual(pf.eps, Decimal('2082.50'))  # 25000 * 8.33%
        self.assertEqual(pf.epf, Decimal('917.50'))

    def test_vpf(self):
        EmployeePFProfile.objects.create(
            employee=self.employee,
            uan='123456789012',
            is_pf_applicable=True,
            voluntary_pf=True,
            vpf_percentage=Decimal('0.0500'),
        )
        rows = [{'component_code': 'BASIC', 'amount': Decimal('15000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertEqual(pf.employee_pf, Decimal('1800.00'))
        self.assertEqual(pf.voluntary_pf, Decimal('750.00'))
        self.assertEqual(pf.total_employee_deduction, Decimal('2550.00'))

    def test_non_pf_employee(self):
        self.employee.pf_eligible = False
        self.employee.save(update_fields=['pf_eligible'])
        rows = [{'component_code': 'BASIC', 'amount': Decimal('15000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertFalse(pf.eligible)
        self.assertEqual(pf.employee_pf, Decimal('0.00'))

    def test_mid_month_join_via_prorated_wages(self):
        rows = [{'component_code': 'BASIC', 'amount': Decimal('10000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertEqual(pf.pf_wages, Decimal('10000.00'))
        self.assertEqual(pf.employee_pf, Decimal('1200.00'))

    def test_exit_before_period(self):
        self.employee.date_of_exit = date(2026, 6, 30)
        self.employee.save(update_fields=['date_of_exit'])
        rows = [{'component_code': 'BASIC', 'amount': Decimal('15000.00'), 'pf_applicable': True}]
        pf = calculate_pf(
            employee=self.employee,
            period=self._period(),
            earning_rows=rows,
            rule_set=self.rule,
        )
        self.assertFalse(pf.eligible)

    def test_fallback_basic_da_when_no_flags(self):
        rows = [
            {'component_code': 'BASIC', 'amount': Decimal('10000.00')},
            {'component_code': 'DA', 'amount': Decimal('2000.00')},
            {'component_code': 'HRA', 'amount': Decimal('4000.00')},
        ]
        self.assertEqual(
            determine_pf_wages_from_components(rows),
            Decimal('12000.00'),
        )


class PFValidationTests(ComplianceTestMixin, TestCase):
    def test_uan_format(self):
        validate_uan('123456789012')
        with self.assertRaises(ValidationError):
            validate_uan('12345')
        self.assertEqual(validate_uan_value(' 123456789012 '), '123456789012')

    def test_missing_uan_when_required(self):
        self.employee.uan = ''
        self.employee.save(update_fields=['uan'])
        errors = validate_employee_pf_for_payroll(self.employee, require_uan=True)
        self.assertTrue(any('UAN' in e for e in errors))

    def test_duplicate_pf_number(self):
        EmployeePFProfile.objects.create(
            employee=self.employee,
            pf_number='AP/ABC/1234567',
            uan='123456789012',
        )
        other = Employee.objects.create(
            company=self.company,
            employee_code='EPF1002',
            first_name='Ram',
            date_of_joining=date(2024, 1, 1),
            basic_salary=Decimal('15000.00'),
            auto_generate_code=False,
        )
        profile = EmployeePFProfile(
            employee=other,
            pf_number='AP/ABC/1234567',
            uan='987654321098',
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()


class PayrollPFIntegrationTests(ComplianceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.period = create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        self.run = create_run(period=self.period, user=self.user)
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company,
            code='EPF91',
            name='EPF Structure',
        )
        basic = SalaryComponent.objects.get(company=self.company, component_code='BASIC')
        SalaryStructureLine.objects.create(
            structure=structure,
            component=basic,
            calculation_type=CalculationType.PERCENTAGE,
            percent=Decimal('40.0000'),
            display_order=10,
        )
        EmployeeSalaryAssignment.objects.create(
            employee=self.employee,
            salary_structure=structure,
            effective_from=date(2024, 1, 1),
            gross_salary=Decimal('50000.00'),
            ctc=Decimal('600000.00'),
            created_by=self.user,
            updated_by=self.user,
        )
        EmployeePFProfile.objects.create(
            employee=self.employee,
            uan='123456789012',
            pf_number='AP/EPF/1001',
            is_pf_applicable=True,
        )

    def test_calculate_run_persists_pf_and_rule_snapshot(self):
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.CALCULATED)
        self.assertEqual(self.run.pf_rule_set_id, self.rule.pk)
        result = PayrollResult.objects.get(run=self.run, employee=self.employee)
        pf = PayrollPFResult.objects.get(payroll_result=result)
        self.assertEqual(pf.rule_version, self.rule.code)
        self.assertEqual(pf.employee_pf, Decimal('1800.00'))
        self.rule.employee_pf_rate = Decimal('0.1000')
        self.rule.save()
        pf.refresh_from_db()
        self.assertEqual(pf.employee_pf, Decimal('1800.00'))
        self.assertEqual(pf.rule_version, 'IN-EPF-2024')

    def test_ecr_row_count(self):
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        rows = iter_ecr_rows(self.run, validate_uans=True)
        self.assertEqual(len(rows), 1)
        text = build_ecr_text(self.run, validate_uans=True)
        self.assertIn('123456789012', text)
        self.assertEqual(len(text.strip().splitlines()), 1)

    def test_ecr_missing_uan_validation(self):
        self.employee.uan = ''
        self.employee.save(update_fields=['uan'])
        self.employee.pf_profile.uan = ''
        self.employee.pf_profile.save(update_fields=['uan'])
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        with self.assertRaises(ValidationError):
            iter_ecr_rows(self.run, validate_uans=True)

    def test_hub_page(self):
        calculate_run(self.run, user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse('compliance:hub'))
        self.assertEqual(response.status_code, 200)

    def test_no_eval_in_pf_engine(self):
        import inspect

        import apps.compliance.services.pf_engine as eng

        source = inspect.getsource(eng)
        self.assertNotIn('eval(', source)
