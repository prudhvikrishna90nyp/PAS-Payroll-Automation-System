from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Client


class ClientModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testadmin',
            password='TestPassword123!',
        )

        self.client_record = Client.objects.create(
            client_code='cli001',
            client_name='Deep Enterprises',
            contact_person='Test Person',
            mobile='9876543210',
            pan='ABCDE1234F',
            gstin='37ABCDE1234F1Z5',
            address_line_1='Naidupet',
            city='Naidupet',
            district='Tirupati',
            state='Andhra Pradesh',
            pincode='524126',
            created_by=self.user,
            updated_by=self.user,
        )

    def test_client_code_saved_in_uppercase(self):
        self.assertEqual(
            self.client_record.client_code,
            'CLI001',
        )

    def test_client_string_representation(self):
        self.assertEqual(
            str(self.client_record),
            'CLI001 - Deep Enterprises',
        )


class ClientViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='TestPassword123!',
        )

        self.client.login(
            username='testuser',
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

    def test_client_list_page(self):
        response = self.client.get(
            reverse('clients:client_list')
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'Deep Enterprises',
        )

    def test_client_search(self):
        response = self.client.get(
            reverse('clients:client_list'),
            {'q': 'Deep'},
        )

        self.assertContains(
            response,
            'Deep Enterprises',
        )

    def test_archive_client(self):
        response = self.client.post(
            reverse(
                'clients:client_archive',
                kwargs={'pk': self.client_record.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse('clients:client_list'),
        )

        self.client_record.refresh_from_db()

        self.assertFalse(
            self.client_record.is_active
        )
