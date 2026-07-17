from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import Client

from .models import Company


class CompanyModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='companyadmin',
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
            pan='ABCDE1234F',
            gstin='37ABCDE1234F1Z5',
            tan='ABCD12345E',
            created_by=self.user,
            updated_by=self.user,
        )

    def test_pan_saved_in_uppercase(self):
        self.assertEqual(self.company.pan, 'ABCDE1234F')

    def test_tan_saved_in_uppercase(self):
        self.company.tan = 'abcd12345e'
        self.company.save()
        self.assertEqual(self.company.tan, 'ABCD12345E')

    def test_company_string_representation(self):
        self.assertEqual(str(self.company), 'Deep Enterprises')


class CompanyFormTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(
            client_code='CLI001',
            client_name='Deep Enterprises',
            mobile='9876543210',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )

    def test_invalid_tan_rejected(self):
        from .forms import CompanyForm

        form = CompanyForm(data={
            'client': self.client_record.pk,
            'company_name': 'Test Company',
            'tan': 'INVALID',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('tan', form.errors)


class CompanyViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission

        self.user = get_user_model().objects.create_user(
            username='companyuser',
            password='TestPassword123!',
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label='company',
                codename__in=[
                    'view_company',
                    'add_company',
                    'change_company',
                    'delete_company',
                ],
            )
        )
        self.client.login(username='companyuser', password='TestPassword123!')

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
            pan='ABCDE1234F',
        )

    def test_company_list_page(self):
        response = self.client.get(reverse('company:company_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Enterprises')

    def test_company_list_filtered_by_client(self):
        response = self.client.get(
            reverse('company:company_list'),
            {'client': self.client_record.pk},
        )
        self.assertContains(response, 'Deep Enterprises')

    def test_company_search(self):
        response = self.client.get(
            reverse('company:company_list'),
            {'q': 'Deep'},
        )
        self.assertContains(response, 'Deep Enterprises')

    def test_company_detail_page(self):
        response = self.client.get(
            reverse('company:company_detail', kwargs={'pk': self.company.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Enterprises')

    def test_archive_company(self):
        response = self.client.post(
            reverse('company:company_archive', kwargs={'pk': self.company.pk})
        )
        self.assertRedirects(response, reverse('company:company_list'))
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_active)

    def test_create_company_with_logo(self):
        import base64

        logo = SimpleUploadedFile(
            'logo.png',
            base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
            ),
            content_type='image/png',
        )
        response = self.client.post(
            reverse('company:company_add'),
            {
                'client': self.client_record.pk,
                'company_name': 'New Company',
                'is_active': True,
                'logo': logo,
            },
        )
        self.assertRedirects(response, reverse('company:company_list'))
        self.assertTrue(
            Company.objects.filter(company_name='New Company', client=self.client_record).exists()
        )


class DeepEnterprisesMigrationTests(TestCase):
    def test_migration_links_deep_enterprises_company(self):
        client_record = Client.objects.create(
            client_code='CLI001',
            client_name='Deep Enterprises',
            mobile='9876543210',
            pan='ABCDE1234F',
            gstin='37ABCDE1234F1Z5',
            address_line_1='Naidupet',
            city='Naidupet',
            state='Andhra Pradesh',
            pincode='524126',
        )
        default_client, _ = Client.objects.get_or_create(
            client_code='DEFAULT',
            defaults={
                'client_name': 'Default Client',
                'mobile': '9000000000',
                'address_line_1': 'Default Address',
                'city': 'Default City',
                'state': 'Andhra Pradesh',
                'pincode': '500001',
            },
        )
        legacy_company = Company.objects.create(
            client=default_client,
            company_name='Deep Enterprises',
            pan='ABCDE1234F',
            gstin='37ABCDE1234F1Z5',
            tan='ABCD12345E',
        )

        import importlib

        class MigrationApps:
            def get_model(self, app_label, model_name):
                if app_label == 'clients' and model_name == 'Client':
                    return Client
                if app_label == 'company' and model_name == 'Company':
                    return Company
                raise LookupError(app_label, model_name)

        migration_module = importlib.import_module(
            'apps.company.migrations.0005_company_audit_and_deep_enterprises'
        )
        migration_module.migrate_deep_enterprises_company(MigrationApps(), None)

        legacy_company.refresh_from_db()
        self.assertEqual(legacy_company.client_id, client_record.pk)
        self.assertEqual(
            Company.objects.filter(
                client=client_record,
                company_name='Deep Enterprises',
                is_active=True,
            ).count(),
            1,
        )
