"""v1.0.0-rc1 stabilization regression tests."""

from datetime import date
from decimal import Decimal
import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.clients.permissions import seed_role_groups as seed_client_groups
from apps.common.utils import format_user_error
from apps.company.models import Company
from apps.company.permissions import seed_role_groups as seed_company_groups
from apps.compliance.permissions import seed_role_groups as seed_compliance_groups
from apps.compliance.services.pf_rules import seed_default_pf_rule_set
from apps.employee.models import Employee
from apps.employee.permissions import seed_role_groups as seed_employee_groups
from apps.payroll.models import (
    CalculationType,
    EmployeeSalaryAssignment,
    PayrollRunStatus,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)
from apps.payroll.permissions import seed_role_groups as seed_payroll_groups
from apps.payroll.seed import seed_standard_components
from apps.payroll.services.payroll_engine import calculate_run, create_period, create_run


User = get_user_model()


class FormatUserErrorTests(TestCase):
    def test_validation_error_list_not_repr(self):
        exc = ValidationError(['Cannot close a period with open runs.'])
        message = format_user_error(exc)
        self.assertEqual(message, 'Cannot close a period with open runs.')
        self.assertNotIn('[', message)


class LegacyPayslipAuthTests(TestCase):
    def test_unauthenticated_payslip_endpoints_redirect(self):
        http = HttpClient()
        for name in ('payroll:payslip_list', 'payroll:payslip_export_excel'):
            response = http.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(
                '/login/' in response.url,
                msg=f'Expected login redirect, got {response.url}',
            )

    def test_authenticated_without_perm_forbidden(self):
        user = User.objects.create_user(username='noperm', password='x')
        http = HttpClient()
        http.force_login(user)
        response = http.get(reverse('payroll:payslip_list'))
        self.assertEqual(response.status_code, 403)


class CompanyClientPermissionTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(
            client_code='CLI-RC1',
            client_name='RC Client',
            mobile='9876543210',
            address_line_1='Addr',
            city='City',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='RC Company',
        )
        self.viewer = User.objects.create_user(username='viewer_rc', password='x')
        view_company = Permission.objects.get(
            content_type__app_label='company',
            codename='view_company',
        )
        view_client = Permission.objects.get(
            content_type__app_label='clients',
            codename='view_client',
        )
        self.viewer.user_permissions.add(view_company, view_client)
        self.http = HttpClient()
        self.http.force_login(self.viewer)

    def test_viewer_cannot_archive_company(self):
        response = self.http.post(
            reverse('company:company_archive', kwargs={'pk': self.company.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.company.refresh_from_db()
        self.assertTrue(self.company.is_active)

    def test_viewer_cannot_archive_client(self):
        response = self.http.post(
            reverse('clients:client_archive', kwargs={'pk': self.client_record.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.client_record.refresh_from_db()
        self.assertTrue(self.client_record.is_active)


class RoleSeedMergeTests(TestCase):
    def test_employee_seed_preserves_payroll_permissions(self):
        seed_payroll_groups()
        admin = Group.objects.get(name='Admin')
        self.assertTrue(admin.permissions.filter(codename='view_payrollrun').exists())
        seed_employee_groups()
        admin.refresh_from_db()
        self.assertTrue(admin.permissions.filter(codename='view_payrollrun').exists())
        self.assertTrue(admin.permissions.filter(codename='view_employee').exists())

    def test_compliance_export_perms_seeded_to_admin(self):
        seed_compliance_groups()
        admin = Group.objects.get(name='Admin')
        for codename in (
            'export_pfregister',
            'export_ecr',
            'export_esiregister',
            'export_ptregister',
            'export_tdsregister',
            'export_form16',
        ):
            self.assertTrue(
                admin.permissions.filter(codename=codename).exists(),
                msg=f'Missing {codename} on Admin',
            )

    def test_company_client_seed_on_admin(self):
        seed_company_groups()
        seed_client_groups()
        admin = Group.objects.get(name='Admin')
        self.assertTrue(admin.permissions.filter(codename='add_company').exists())
        self.assertTrue(admin.permissions.filter(codename='add_client').exists())
        self.assertTrue(admin.permissions.filter(codename='add_branch').exists())
        viewer = Group.objects.get(name='Viewer')
        self.assertTrue(viewer.permissions.filter(codename='view_company').exists())
        self.assertFalse(viewer.permissions.filter(codename='add_company').exists())


class PayrollVolumeSmokeTests(TestCase):
    """Simple performance/smoke baseline for larger employee volumes."""

    def setUp(self):
        self.user = User.objects.create_user(username='vol', password='x')
        self.client_record = Client.objects.create(
            client_code='VOL1',
            client_name='Volume Client',
            mobile='9000000000',
            address_line_1='A',
            city='C',
            state='Andhra Pradesh',
            pincode='500001',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='Volume Co',
        )
        seed_default_pf_rule_set()
        seed_standard_components(self.company)
        structure = SalaryStructure.objects.create(
            company=self.company,
            code='VOLSTD',
            name='Volume Structure',
        )
        basic = SalaryComponent.objects.get(company=self.company, component_code='BASIC')
        SalaryStructureLine.objects.create(
            structure=structure,
            component=basic,
            calculation_type=CalculationType.PERCENTAGE,
            percent=Decimal('40.0000'),
            display_order=10,
        )
        self.period = create_period(
            company=self.company,
            month=4,
            year=2026,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            user=self.user,
        )
        for i in range(20):
            emp = Employee.objects.create(
                company=self.company,
                employee_code=f'V{i:03d}',
                first_name='Emp',
                last_name=str(i),
                date_of_joining=date(2025, 1, 1),
                basic_salary=Decimal('30000.00'),
                auto_generate_code=False,
            )
            EmployeeSalaryAssignment.objects.create(
                employee=emp,
                salary_structure=structure,
                effective_from=date(2025, 1, 1),
                gross_salary=Decimal('50000.00'),
                ctc=Decimal('600000.00'),
                created_by=self.user,
                updated_by=self.user,
            )

    def test_calculate_twenty_employees_under_budget(self):
        run = create_run(period=self.period, company=self.company, user=self.user)
        started = time.perf_counter()
        calculate_run(run, user=self.user)
        elapsed = time.perf_counter() - started
        run.refresh_from_db()
        self.assertEqual(run.status, PayrollRunStatus.CALCULATED)
        self.assertEqual(run.results.count(), 20)
        # Soft baseline for local SQLite; flag only if pathologically slow.
        self.assertLess(elapsed, 60.0, msg=f'calculate_run took {elapsed:.2f}s for 20 employees')
