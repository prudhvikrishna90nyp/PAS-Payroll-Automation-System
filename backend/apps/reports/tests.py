from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client
from apps.company.models import Company
from apps.employee.models import Employee


class EmployeeReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='reportuser',
            password='TestPassword123!',
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename='view_employee', content_type__app_label='employee')
        )
        client = Client.objects.create(
            client_code='CLI100',
            client_name='Report Client',
            mobile='9876543210',
            address_line_1='Main Road',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        self.company = Company.objects.create(client=client, company_name='Report Co')
        Employee.objects.create(
            company=self.company,
            employee_code='EMP0001',
            first_name='PF',
            last_name='Worker',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('20000.00'),
            auto_generate_code=False,
            pf_eligible=True,
            esi_eligible=False,
        )
        Employee.objects.create(
            company=self.company,
            employee_code='EMP0002',
            first_name='ESI',
            last_name='Worker',
            date_of_joining=date(2026, 1, 1),
            basic_salary=Decimal('18000.00'),
            auto_generate_code=False,
            pf_eligible=False,
            esi_eligible=True,
        )
        self.client.login(username='reportuser', password='TestPassword123!')

    def test_reports_index(self):
        response = self.client.get(reverse('reports_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Employee Register')

    def test_employee_register_report(self):
        response = self.client.get(reverse('employee_register_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PF Worker')
        self.assertContains(response, 'ESI Worker')

    def test_pf_employees_report(self):
        response = self.client.get(reverse('pf_employees_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PF Worker')
        self.assertNotContains(response, 'ESI Worker')

    def test_esi_employees_report(self):
        response = self.client.get(reverse('esi_employees_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ESI Worker')
        self.assertNotContains(response, 'PF Worker')

    def test_unauthenticated_report_redirects(self):
        self.client.logout()
        response = self.client.get(reverse('employee_register_report'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
