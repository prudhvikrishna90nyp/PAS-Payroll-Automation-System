from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.company.models import Branch, Company, Department, Designation

from io import BytesIO

from openpyxl import Workbook

from .forms import EmployeeForm
from .import_export import import_employees
from .models import DocumentType, Employee, SalaryStructure
from .permissions import ROLE_GROUPS, seed_role_groups
from .services import generate_employee_code


def _employee_permission(codename):
    return Permission.objects.get(codename=codename, content_type__app_label='employee')


class EmployeeTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='empadmin',
            password='TestPassword123!',
        )
        for codename in (
            'view_employee',
            'add_employee',
            'change_employee',
            'delete_employee',
            'view_employeedocument',
            'add_employeedocument',
            'change_employeedocument',
            'delete_employeedocument',
        ):
            self.user.user_permissions.add(_employee_permission(codename))

        self.client_record = Client.objects.create(
            client_code='CLI001',
            client_name='Deep Enterprises',
            mobile='9876543210',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(
            client=self.client_record,
            company_name='Deep Enterprises',
        )
        self.branch = Branch.objects.create(
            company=self.company,
            branch_name='Head Office',
            code='HO',
        )
        self.department = Department.objects.create(
            company=self.company,
            name='Finance',
            code='FIN',
        )
        self.designation = Designation.objects.create(
            company=self.company,
            name='Manager',
            code='MGR',
        )


class EmployeeModelTests(EmployeeTestMixin, TestCase):
    def test_auto_generate_employee_code(self):
        employee = Employee.objects.create(
            company=self.company,
            first_name='Ravi',
            last_name='Kumar',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('25000.00'),
            auto_generate_code=True,
        )
        self.assertEqual(employee.employee_code, 'EMP0001')

    def test_generate_employee_code_increments(self):
        Employee.objects.create(
            company=self.company,
            employee_code='EMP0005',
            first_name='Existing',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
        )
        self.assertEqual(generate_employee_code(self.company), 'EMP0006')

    def test_pan_saved_in_uppercase(self):
        employee = Employee.objects.create(
            company=self.company,
            employee_code='EMP0100',
            first_name='Test',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            pan='abcde1234f',
            auto_generate_code=False,
        )
        self.assertEqual(employee.pan, 'ABCDE1234F')

    def test_employee_id_alias(self):
        employee = Employee.objects.create(
            company=self.company,
            employee_code='EMP0200',
            first_name='Alias',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
        )
        self.assertEqual(employee.employee_id, 'EMP0200')

    def test_employment_type_default(self):
        employee = Employee.objects.create(
            company=self.company,
            first_name='Type',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=True,
        )
        self.assertEqual(employee.employment_type, 'permanent')


class EmployeeFormTests(EmployeeTestMixin, TestCase):
    def test_duplicate_employee_code_rejected(self):
        Employee.objects.create(
            company=self.company,
            employee_code='EMP0001',
            first_name='Existing',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
        )
        form = EmployeeForm(data={
            'company': self.company.pk,
            'employee_code': 'emp0001',
            'auto_generate_code': False,
            'first_name': 'New',
            'date_of_joining': '2026-02-01',
            'basic_salary': '22000',
            'employment_type': 'permanent',
            'employment_status': 'active',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('employee_code', form.errors)

    def test_branch_must_belong_to_company(self):
        other_company = Company.objects.create(
            client=self.client_record,
            company_name='Other Company',
        )
        other_branch = Branch.objects.create(
            company=other_company,
            branch_name='Other Branch',
            code='OB',
        )
        form = EmployeeForm(data={
            'company': self.company.pk,
            'branch': other_branch.pk,
            'employee_code': 'EMP0099',
            'auto_generate_code': False,
            'first_name': 'Wrong',
            'date_of_joining': '2026-02-01',
            'basic_salary': '22000',
            'employment_type': 'permanent',
            'employment_status': 'active',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('branch', form.errors)

    def test_invalid_pan_and_bank_account_rejected(self):
        form = EmployeeForm(data={
            'company': self.company.pk,
            'auto_generate_code': True,
            'first_name': 'Invalid',
            'pan': 'BADPAN',
            'bank_account_number': '12',
            'date_of_joining': '2026-02-01',
            'basic_salary': '22000',
            'employment_type': 'permanent',
            'employment_status': 'active',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('pan', form.errors)
        self.assertIn('bank_account_number', form.errors)


class EmployeeImportTests(EmployeeTestMixin, TestCase):
    def _build_workbook(self, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            'Employee Code', 'First Name', 'Last Name', 'Email', 'Mobile',
            'Branch Code', 'Department Code', 'Designation Code',
            'Date of Joining', 'Basic Salary', 'PAN', 'Aadhaar', 'UAN',
            'ESIC Number', 'PF Eligible', 'ESI Eligible', 'Employment Type',
            'Employment Status', 'Bank Name', 'Account Number', 'IFSC',
        ])
        for row in rows:
            sheet.append(row)
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    def test_import_creates_valid_rows(self):
        workbook = self._build_workbook([
            [
                'EMP9001', 'Imported', 'User', 'imp@example.com', '9876543210',
                'HO', 'FIN', 'MGR', date(2026, 4, 1), 28000, 'ABCDE1234F',
                '123456789012', '', '', 'Yes', 'No', 'permanent', 'active',
                'SBI', '123456789012', 'SBIN0001234',
            ],
        ])
        created, skipped, errors = import_employees(self.company, workbook, self.user)
        self.assertEqual(created, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(errors, [])
        self.assertTrue(Employee.objects.filter(employee_code='EMP9001').exists())

    def test_import_skips_duplicates(self):
        Employee.objects.create(
            company=self.company,
            employee_code='EMP9001',
            first_name='Existing',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
        )
        workbook = self._build_workbook([
            [
                'EMP9001', 'Dup', 'User', '', '9876543210',
                'HO', 'FIN', 'MGR', date(2026, 4, 1), 28000, '',
                '', '', '', 'Yes', 'No', 'permanent', 'active',
                '', '', '',
            ],
        ])
        created, skipped, errors = import_employees(self.company, workbook, self.user)
        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(errors), 1)

    def test_document_types_cover_sprint_list(self):
        for expected in (
            'aadhaar', 'pan', 'appointment', 'resume', 'educational',
            'bank_passbook', 'pf_form', 'esi_card', 'other',
        ):
            self.assertIn(expected, DocumentType.values)


class EmployeeViewTests(EmployeeTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='empadmin', password='TestPassword123!')
        self.employee = Employee.objects.create(
            company=self.company,
            branch=self.branch,
            department=self.department,
            designation=self.designation,
            employee_code='EMP0001',
            first_name='Ravi',
            last_name='Kumar',
            mobile='9876543210',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('25000.00'),
            auto_generate_code=False,
            pf_eligible=True,
            esi_eligible=True,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_employee_list_page(self):
        response = self.client.get(reverse('employees:employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ravi Kumar')

    def test_employee_search(self):
        response = self.client.get(reverse('employees:employee_list'), {'q': 'Ravi'})
        self.assertContains(response, 'Ravi Kumar')

    def test_employee_filter_pf_eligible(self):
        response = self.client.get(
            reverse('employees:employee_list'),
            {'pf_eligible': 'yes', 'status': 'active'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ravi Kumar')

    def test_employee_detail_page(self):
        response = self.client.get(
            reverse('employees:employee_detail', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP0001')
        self.assertContains(response, 'Personal')
        self.assertContains(response, 'Employment')
        self.assertContains(response, 'Payroll')
        self.assertContains(response, 'Statutory')
        self.assertContains(response, 'Bank')
        self.assertContains(response, 'Documents')

    def test_document_upload_on_profile(self):
        upload = SimpleUploadedFile('aadhaar.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.post(
            reverse('employees:employee_detail', kwargs={'pk': self.employee.pk}),
            {
                'document_type': DocumentType.AADHAAR,
                'title': 'Aadhaar Card',
                'file': upload,
            },
        )
        self.assertRedirects(
            response,
            reverse('employees:employee_detail', kwargs={'pk': self.employee.pk}),
        )
        self.assertEqual(self.employee.documents.count(), 1)

    def test_create_employee_with_photo(self):
        import base64

        photo = SimpleUploadedFile(
            'photo.png',
            base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
            ),
            content_type='image/png',
        )
        response = self.client.post(
            reverse('employees:employee_add'),
            {
                'company': self.company.pk,
                'branch': self.branch.pk,
                'department': self.department.pk,
                'designation': self.designation.pk,
                'auto_generate_code': 'on',
                'first_name': 'New',
                'last_name': 'Employee',
                'date_of_joining': '2026-03-01',
                'basic_salary': '30000',
                'employment_type': 'permanent',
                'employment_status': 'active',
                'is_active': 'on',
                'pf_eligible': 'on',
                'photo': photo,
            },
        )
        self.assertRedirects(response, reverse('employees:employee_list'))
        self.assertTrue(Employee.objects.filter(first_name='New', company=self.company).exists())

    def test_archive_employee(self):
        response = self.client.post(
            reverse('employees:employee_archive', kwargs={'pk': self.employee.pk})
        )
        self.assertRedirects(response, reverse('employees:employee_list'))
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

    def test_export_employees(self):
        response = self.client.get(reverse('employees:employee_export'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_export_employees_pdf(self):
        class FakeHTML:
            def __init__(self, *args, **kwargs):
                pass

            def write_pdf(self):
                return b'%PDF-1.4 mock'

        fake_weasyprint = MagicMock()
        fake_weasyprint.HTML = FakeHTML
        with patch.dict(sys.modules, {'weasyprint': fake_weasyprint}):
            response = self.client.get(
                reverse('employees:employee_export_pdf'),
                {'status': 'active', 'report': 'register'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_unauthenticated_list_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('employees:employee_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_unauthenticated_export_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('employees:employee_export'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_viewer_cannot_add_employee(self):
        viewer = get_user_model().objects.create_user(
            username='viewer',
            password='TestPassword123!',
        )
        viewer.user_permissions.add(_employee_permission('view_employee'))
        self.client.logout()
        self.client.login(username='viewer', password='TestPassword123!')
        response = self.client.get(reverse('employees:employee_add'))
        self.assertEqual(response.status_code, 403)

    def test_import_error_log_download(self):
        session = self.client.session
        session['employee_import_errors'] = ['Row 2: First name is required.']
        session.save()
        response = self.client.post(
            reverse('employees:employee_import'),
            {'download_errors': '1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class EmployeeRoleSeedTests(TestCase):
    def test_seed_role_groups_creates_expected_groups(self):
        names = seed_role_groups()
        self.assertEqual(set(names), set(ROLE_GROUPS.keys()))
        for name in ROLE_GROUPS:
            self.assertTrue(Group.objects.filter(name=name).exists())
        hr = Group.objects.get(name='HR')
        self.assertTrue(hr.permissions.filter(codename='view_employee').exists())
        self.assertTrue(hr.permissions.filter(codename='add_employee').exists())
        self.assertFalse(hr.permissions.filter(codename='delete_employee').exists())
        viewer = Group.objects.get(name='Viewer')
        self.assertTrue(viewer.permissions.filter(codename='view_employee').exists())
        self.assertFalse(viewer.permissions.filter(codename='add_employee').exists())


class SalaryStructureTests(EmployeeTestMixin, TestCase):
    def test_salary_structure_unique_code_per_company(self):
        SalaryStructure.objects.create(
            company=self.company,
            name='Standard',
            code='STD',
            basic_salary=Decimal('25000.00'),
        )
        with self.assertRaises(Exception):
            SalaryStructure.objects.create(
                company=self.company,
                name='Duplicate',
                code='STD',
                basic_salary=Decimal('26000.00'),
            )
