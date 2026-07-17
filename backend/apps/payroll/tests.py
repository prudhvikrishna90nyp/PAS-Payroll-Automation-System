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
    PayrollAuditLog,
    PayrollPeriod,
    PayrollPeriodStatus,
    PayrollResult,
    PayrollResultComponent,
    PayrollRun,
    PayrollRunStatus,
    RoundingRule,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)
from .permissions import seed_role_groups
from .seed import seed_standard_components
from .services.calculator import calculate_employee, compute_payable_days, compute_proration_factor
from .services.exceptions import LockedRunError, RunNotCalculableError
from .services.formula_engine import (
    FormulaError,
    detect_circular_references,
    evaluate_formula,
    extract_references,
)
from .services.payroll_engine import (
    calculate_run,
    close_period,
    create_period,
    create_run,
    open_period,
)
from .services.payslip_generator import calculate_payslip_amounts, generate_payslip
from .services.salary_calculator import apply_rounding, calculate_structure_components
from .services.validation import (
    SalaryValidationError,
    validate_component,
    validate_payroll_period,
    validate_structure,
)


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
            'view_payrollperiod',
            'add_payrollperiod',
            'change_payrollperiod',
            'view_payrollrun',
            'add_payrollrun',
            'change_payrollrun',
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


class PayrollPeriodFoundationTests(PayrollTestMixin, TestCase):
    def test_period_unique_company_month_year(self):
        create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        with self.assertRaises(SalaryValidationError):
            create_period(
                company=self.company,
                month=7,
                year=2026,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
                user=self.user,
            )

    def test_period_overlap_prevention(self):
        create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        period = PayrollPeriod(
            company=self.company,
            month=8,
            year=2026,
            start_date=date(2026, 7, 15),
            end_date=date(2026, 8, 14),
        )
        errors = validate_payroll_period(period)
        self.assertTrue(any('overlaps' in e.lower() for e in errors))

    def test_open_close_period(self):
        period = create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        self.assertEqual(period.status, PayrollPeriodStatus.OPEN)
        close_period(period, user=self.user)
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriodStatus.CLOSED)
        open_period(period, user=self.user)
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriodStatus.OPEN)

    def test_audit_log_on_period_close(self):
        period = create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        close_period(period, user=self.user)
        self.assertTrue(
            PayrollAuditLog.objects.filter(period=period, action='period_close').exists()
        )


class PayrollRunFoundationTests(PayrollTestMixin, TestCase):
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

    def test_create_draft_run(self):
        run = create_run(period=self.period, user=self.user, notes='First draft')
        self.assertEqual(run.status, PayrollRunStatus.DRAFT)
        self.assertEqual(run.run_number, 1)
        self.assertEqual(run.company_id, self.company.pk)

    def test_audit_log_on_run_create(self):
        run = create_run(period=self.period, user=self.user)
        self.assertTrue(
            PayrollAuditLog.objects.filter(run=run, action='run_create').exists()
        )

    def test_cannot_create_run_on_closed_period(self):
        close_period(self.period, user=self.user)
        with self.assertRaises(SalaryValidationError):
            create_run(period=self.period, user=self.user)

    def test_run_number_increments(self):
        create_run(period=self.period, user=self.user)
        run2 = create_run(period=self.period, user=self.user)
        self.assertEqual(run2.run_number, 2)


class PayrollEngineAuthViewTests(PayrollTestMixin, TestCase):
    def test_period_list_requires_login(self):
        response = self.client.get(reverse('payroll:period_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_run_list_requires_login(self):
        response = self.client.get(reverse('payroll:run_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_period_list_ok(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payroll:period_list'))
        self.assertEqual(response.status_code, 200)

    def test_run_create_view(self):
        period = create_period(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            user=self.user,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('payroll:run_add'),
            {'period': period.pk, 'notes': 'UI create'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PayrollRun.objects.filter(period=period, status=PayrollRunStatus.DRAFT).exists()
        )


class PayrollCalculationEngineTests(PayrollTestMixin, TestCase):
    """Sprint 8.2 — calculate_run pipeline and proration."""

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
        self.structure = self._build_structure()
        self.assignment = EmployeeSalaryAssignment.objects.create(
            employee=self.employee,
            salary_structure=self.structure,
            effective_from=date(2026, 1, 1),
            gross_salary=Decimal('50000.00'),
            ctc=Decimal('600000.00'),
            created_by=self.user,
            updated_by=self.user,
        )

    def _build_structure(self):
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company,
            code='CALC82',
            name='Calc Engine Structure',
        )
        basic = SalaryComponent.objects.get(company=self.company, component_code='BASIC')
        hra = SalaryComponent.objects.get(company=self.company, component_code='HRA')
        conv = SalaryComponent.objects.get(company=self.company, component_code='CONVEYANCE')
        SalaryStructureLine.objects.create(
            structure=structure,
            component=basic,
            calculation_type=CalculationType.PERCENTAGE,
            percent=Decimal('40.0000'),
            display_order=10,
        )
        SalaryStructureLine.objects.create(
            structure=structure,
            component=hra,
            calculation_type=CalculationType.FORMULA,
            formula_override='Basic * 40 / 100',
            display_order=20,
        )
        SalaryStructureLine.objects.create(
            structure=structure,
            component=conv,
            calculation_type=CalculationType.FIXED,
            value=Decimal('1600.00'),
            display_order=30,
        )
        return structure

    def _att_period(self):
        from apps.attendance.models import AttendancePeriod, PeriodStatus

        return AttendancePeriod.objects.create(
            company=self.company,
            month=7,
            year=2026,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            status=PeriodStatus.LOCKED,
        )

    def test_full_month_employee(self):
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.CALCULATED)
        result = PayrollResult.objects.get(run=self.run, employee=self.employee)
        # 40% basic + 40% HRA of basic + 1600 conveyance = 20000 + 8000 + 1600
        self.assertEqual(result.total_earnings, Decimal('29600.00'))
        self.assertEqual(result.gross, Decimal('29600.00'))
        self.assertEqual(result.net_salary, result.gross - result.total_deductions)
        codes = set(
            PayrollResultComponent.objects.filter(result=result).values_list(
                'component_code', flat=True
            )
        )
        self.assertIn('BASIC', codes)
        self.assertIn('STAT_PF', codes)
        pf = PayrollResultComponent.objects.get(result=result, component_code='STAT_PF')
        self.assertEqual(pf.amount, Decimal('0.00'))

    def test_mid_month_joining_proration(self):
        self.employee.date_of_joining = date(2026, 7, 16)
        self.employee.save(update_fields=['date_of_joining'])
        calc = calculate_employee(employee=self.employee, period=self.period)
        # Jul 16–31 = 16 eligible / 31 calendar
        self.assertEqual(calc.eligible_days, Decimal('16'))
        self.assertEqual(calc.calendar_days, Decimal('31'))
        expected_factor = compute_proration_factor(Decimal('16'), Decimal('31'))
        self.assertEqual(calc.proration_factor, expected_factor)
        full_earnings = Decimal('29600.00')
        expected = (full_earnings * expected_factor).quantize(Decimal('0.01'))
        self.assertEqual(calc.total_earnings, expected)

    def test_lop_proration(self):
        from apps.attendance.models import AttendanceMonthlySummary

        att_period = self._att_period()
        # 31 eligible; present+leave+WO+holiday = 28 → payable 28 (3 LOP implied)
        AttendanceMonthlySummary.objects.create(
            employee=self.employee,
            period=att_period,
            present_days=Decimal('20.00'),
            paid_leave_days=Decimal('2.00'),
            weekly_off_days=Decimal('4.00'),
            holiday_days=Decimal('2.00'),
            lop_days=Decimal('3.00'),
            absent_days=Decimal('3.00'),
        )
        calc = calculate_employee(employee=self.employee, period=self.period)
        self.assertEqual(calc.payable_days, Decimal('28.00'))
        factor = compute_proration_factor(Decimal('28'), Decimal('31'))
        self.assertEqual(calc.proration_factor, factor)

    def test_half_day_counts_as_half_present(self):
        from apps.attendance.models import AttendanceMonthlySummary
        from apps.payroll.services.attendance_loader import AttendanceSnapshot

        # present_days already includes half-day * 0.5 per attendance services
        snap = AttendanceSnapshot(
            present_days=Decimal('0.50'),
            half_days=Decimal('1.00'),
            source='summary',
        )
        payable = compute_payable_days(eligible_days=Decimal('31'), attendance=snap)
        self.assertEqual(payable, Decimal('0.50'))

        att_period = self._att_period()
        AttendanceMonthlySummary.objects.create(
            employee=self.employee,
            period=att_period,
            present_days=Decimal('0.50'),
            half_days=Decimal('1.00'),
            lop_days=Decimal('0.00'),
        )
        calc = calculate_employee(employee=self.employee, period=self.period)
        self.assertEqual(calc.payable_days, Decimal('0.50'))
        self.assertEqual(calc.present_days, Decimal('0.50'))

    def test_fixed_percentage_formula_components(self):
        calculate_run(self.run, user=self.user)
        result = PayrollResult.objects.get(run=self.run, employee=self.employee)
        by_code = {
            c.component_code: c.amount
            for c in result.components.all()
            if c.component_type == ComponentType.EARNING
        }
        self.assertEqual(by_code['BASIC'], Decimal('20000.00'))
        self.assertEqual(by_code['HRA'], Decimal('8000.00'))
        self.assertEqual(by_code['CONVEYANCE'], Decimal('1600.00'))

    def test_rounding_nearest_rupee(self):
        component = SalaryComponent.objects.create(
            company=self.company,
            component_code='ROUNDT',
            component_name='Rounding Test',
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.FIXED,
            rounding_rule=RoundingRule.NEAREST,
        )
        amount = apply_rounding(Decimal('100.60'), RoundingRule.NEAREST)
        self.assertEqual(amount, Decimal('101.00'))
        amount_down = apply_rounding(Decimal('100.40'), RoundingRule.NEAREST)
        self.assertEqual(amount_down, Decimal('100.00'))
        self.assertEqual(component.rounding_rule, RoundingRule.NEAREST)

    def test_missing_salary_assignment(self):
        self.assignment.soft_delete()
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.INCOMPLETE)
        self.assertTrue(self.run.calculation_errors)
        self.assertEqual(self.run.calculation_errors[0]['code'], 'missing_salary_assignment')
        self.assertFalse(
            PayrollResult.objects.filter(run=self.run, employee=self.employee).exists()
        )

    def test_invalid_formula(self):
        SalaryStructureLine.objects.filter(
            structure=self.structure, component__component_code='HRA'
        ).update(formula_override='Basic / 0')
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.INCOMPLETE)
        self.assertIn('Division by zero', self.run.calculation_errors[0]['error'])
        self.assertFalse(
            PayrollResult.objects.filter(run=self.run, employee=self.employee).exists()
        )

    def test_circular_formula(self):
        SalaryStructureLine.objects.filter(
            structure=self.structure, component__component_code='BASIC'
        ).update(
            calculation_type=CalculationType.FORMULA,
            formula_override='HRA',
            percent=None,
        )
        SalaryStructureLine.objects.filter(
            structure=self.structure, component__component_code='HRA'
        ).update(formula_override='Basic')
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.INCOMPLETE)
        self.assertTrue(
            any('circular' in e['error'].lower() for e in self.run.calculation_errors)
        )

    def test_locked_run_rejection(self):
        self.run.status = PayrollRunStatus.LOCKED
        self.run.save(update_fields=['status'])
        with self.assertRaises(LockedRunError):
            calculate_run(self.run, user=self.user)

    def test_reviewed_run_rejection(self):
        self.run.status = PayrollRunStatus.REVIEWED
        self.run.save(update_fields=['status'])
        with self.assertRaises(RunNotCalculableError):
            calculate_run(self.run, user=self.user)

    def test_recalculation_unlocked_replaces_results(self):
        calculate_run(self.run, user=self.user)
        first_id = PayrollResult.objects.get(run=self.run).pk
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.CALCULATED)
        self.assertEqual(PayrollResult.objects.filter(run=self.run).count(), 1)
        self.assertNotEqual(PayrollResult.objects.get(run=self.run).pk, first_id)

    def test_duplicate_calc_prevention_for_locked(self):
        calculate_run(self.run, user=self.user)
        self.run.status = PayrollRunStatus.LOCKED
        self.run.save(update_fields=['status'])
        with self.assertRaises(LockedRunError):
            calculate_run(self.run, user=self.user)
        self.assertEqual(PayrollResult.objects.filter(run=self.run).count(), 1)

    def test_transaction_rollback_on_unexpected_failure(self):
        calculate_run(self.run, user=self.user)
        self.assertEqual(PayrollResult.objects.filter(run=self.run).count(), 1)
        from unittest.mock import patch

        with patch(
            'apps.payroll.services.payroll_engine.snapshot_employee_result',
            side_effect=RuntimeError('boom'),
        ):
            with self.assertRaises(RuntimeError):
                calculate_run(self.run, user=self.user)
        # Outer atomic rolls back: prior successful result remains (delete+fail undone)
        self.run.refresh_from_db()
        self.assertEqual(PayrollResult.objects.filter(run=self.run).count(), 1)
        self.assertEqual(self.run.status, PayrollRunStatus.CALCULATED)

    def test_partial_failure_keeps_successful_employee(self):
        emp2 = Employee.objects.create(
            company=self.company,
            employee_code='EMP7002',
            first_name='No',
            last_name='Assign',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('10000.00'),
            auto_generate_code=False,
        )
        calculate_run(self.run, user=self.user)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.INCOMPLETE)
        self.assertTrue(
            PayrollResult.objects.filter(run=self.run, employee=self.employee).exists()
        )
        self.assertFalse(
            PayrollResult.objects.filter(run=self.run, employee=emp2).exists()
        )
        self.assertEqual(len(self.run.calculation_errors), 1)
        self.assertEqual(self.run.calculation_errors[0]['employee_code'], 'EMP7002')

    def test_calculate_view_ui(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('payroll:run_calculate', args=[self.run.pk]))
        self.assertEqual(response.status_code, 302)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, PayrollRunStatus.CALCULATED)
        detail = self.client.get(reverse('payroll:run_detail', args=[self.run.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Totals')
        self.assertContains(detail, 'EMP7001')
