from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client

from .forms import BranchForm, DepartmentForm, DesignationForm
from .models import Branch, Company, Department, Designation


class OrganisationTestMixin:
    def setUp(self):
        from django.contrib.auth.models import Permission

        self.user = get_user_model().objects.create_user(
            username='orguser',
            password='TestPassword123!',
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label='company',
                codename__in=[
                    'view_branch',
                    'add_branch',
                    'change_branch',
                    'delete_branch',
                    'view_department',
                    'add_department',
                    'change_department',
                    'delete_department',
                    'view_designation',
                    'add_designation',
                    'change_designation',
                    'delete_designation',
                ],
            )
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


class BranchModelTests(OrganisationTestMixin, TestCase):
    def test_branch_code_saved_in_uppercase(self):
        branch = Branch.objects.create(
            company=self.company,
            branch_name='Head Office',
            code='ho01',
        )
        self.assertEqual(branch.code, 'HO01')

    def test_unique_code_per_company(self):
        Branch.objects.create(company=self.company, branch_name='Branch A', code='BR01')
        with self.assertRaises(Exception):
            Branch.objects.create(company=self.company, branch_name='Branch B', code='br01')


class DepartmentModelTests(OrganisationTestMixin, TestCase):
    def test_department_code_saved_in_uppercase(self):
        department = Department.objects.create(
            company=self.company,
            name='Accounts',
            code='acc',
        )
        self.assertEqual(department.code, 'ACC')


class DesignationModelTests(OrganisationTestMixin, TestCase):
    def test_designation_code_saved_in_uppercase(self):
        designation = Designation.objects.create(
            company=self.company,
            name='Manager',
            code='mgr',
        )
        self.assertEqual(designation.code, 'MGR')


class OrganisationFormTests(OrganisationTestMixin, TestCase):
    def test_duplicate_branch_code_rejected(self):
        Branch.objects.create(company=self.company, branch_name='Main', code='HO')
        form = BranchForm(data={
            'company': self.company.pk,
            'branch_name': 'Duplicate',
            'code': 'ho',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_duplicate_department_code_rejected(self):
        Department.objects.create(company=self.company, name='HR', code='HR')
        form = DepartmentForm(data={
            'company': self.company.pk,
            'name': 'Human Resources',
            'code': 'hr',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)


class BranchViewTests(OrganisationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='orguser', password='TestPassword123!')
        self.branch = Branch.objects.create(
            company=self.company,
            branch_name='Head Office',
            code='HO',
        )

    def test_branch_list_page(self):
        response = self.client.get(reverse('organisation:branch_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Head Office')

    def test_branch_list_filtered_by_company(self):
        response = self.client.get(
            reverse('organisation:branch_list'),
            {'company': self.company.pk},
        )
        self.assertContains(response, 'Head Office')

    def test_archive_branch(self):
        response = self.client.post(
            reverse('organisation:branch_archive', kwargs={'pk': self.branch.pk})
        )
        self.assertRedirects(response, reverse('organisation:branch_list'))
        self.branch.refresh_from_db()
        self.assertFalse(self.branch.is_active)


class DepartmentViewTests(OrganisationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='orguser', password='TestPassword123!')
        self.department = Department.objects.create(
            company=self.company,
            name='Finance',
            code='FIN',
        )

    def test_department_list_page(self):
        response = self.client.get(reverse('organisation:department_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Finance')

    def test_create_department(self):
        response = self.client.post(
            reverse('organisation:department_add'),
            {
                'company': self.company.pk,
                'name': 'Human Resources',
                'code': 'HR',
                'description': 'HR department',
                'is_active': True,
            },
        )
        self.assertRedirects(response, reverse('organisation:department_list'))
        self.assertTrue(
            Department.objects.filter(company=self.company, code='HR').exists()
        )


class DesignationViewTests(OrganisationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='orguser', password='TestPassword123!')
        self.designation = Designation.objects.create(
            company=self.company,
            name='Supervisor',
            code='SUP',
        )

    def test_designation_list_page(self):
        response = self.client.get(reverse('organisation:designation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supervisor')

    def test_archive_designation(self):
        response = self.client.post(
            reverse('organisation:designation_archive', kwargs={'pk': self.designation.pk})
        )
        self.assertRedirects(response, reverse('organisation:designation_list'))
        self.designation.refresh_from_db()
        self.assertFalse(self.designation.is_active)
