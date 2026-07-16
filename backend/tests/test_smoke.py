from django.test import Client, TestCase
from django.urls import reverse


class SmokeTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_admin_login_page(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
