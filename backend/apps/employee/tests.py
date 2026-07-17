from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.company.models import Branch, Company, Department, Designation

from .forms import EmployeeForm
from .models import Employee, SalaryStructure
from .services import generate_employee_code


class EmployeeTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='empadmin',
            password='TestPassword123!',
        )
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
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('branch', form.errors)


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

    def test_employee_detail_page(self):
        response = self.client.get(
            reverse('employees:employee_detail', kwargs={'pk': self.employee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP0001')

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
