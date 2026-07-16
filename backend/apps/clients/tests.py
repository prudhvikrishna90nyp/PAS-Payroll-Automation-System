from django.contrib.auth.models import User
from django.test import Client as TestClient, TestCase
from django.urls import reverse

from apps.clients.models import Client


class ClientModelTests(TestCase):
    def test_str_returns_name(self):
        client = Client.objects.create(name='Acme Corp', code='ACME')
        self.assertEqual(str(client), 'Acme Corp')

    def test_soft_delete_marks_inactive(self):
        client = Client.objects.create(name='Acme Corp', code='ACME')
        client.soft_delete()
        client.refresh_from_db()
        self.assertTrue(client.is_deleted)
        self.assertFalse(client.is_active)
        self.assertIsNotNone(client.deleted_at)
        self.assertNotIn(client, Client.objects.all())
        self.assertIn(client, Client.all_objects.all())


class ClientViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hr', password='pass1234')
        self.http = TestClient()
        self.http.login(username='hr', password='pass1234')

    def test_client_list_requires_login(self):
        anon = TestClient()
        response = anon.get(reverse('client_list'))
        self.assertEqual(response.status_code, 302)

    def test_client_create_and_list(self):
        response = self.http.post(reverse('client_create'), {
            'name': 'Globex',
            'code': 'GLBX',
            'contact_person': 'Jane',
            'phone': '9999999999',
            'email': 'jane@globex.com',
            'address': 'Mumbai',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Client.objects.filter(code='GLBX').exists())

        response = self.http.get(reverse('client_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Globex')

    def test_client_update(self):
        client = Client.objects.create(name='Old Name', code='OLD')
        response = self.http.post(reverse('client_update', args=[client.pk]), {
            'name': 'New Name',
            'code': 'OLD',
            'contact_person': '',
            'phone': '',
            'email': '',
            'address': '',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        self.assertEqual(client.name, 'New Name')

    def test_client_soft_delete_via_view(self):
        client = Client.objects.create(name='Remove Me', code='RMV')
        response = self.http.post(reverse('client_delete', args=[client.pk]))
        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        self.assertTrue(client.is_deleted)
