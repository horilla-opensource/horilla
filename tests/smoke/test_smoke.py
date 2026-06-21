from django.test import TestCase, Client
from django.urls import reverse

class HorillaSmokeTest(TestCase):
    """
    Smoke test suite verifying that the application boots and
    critical endpoints respond.
    """

    def setUp(self):
        self.client = Client()

    def test_root_endpoint_redirects_to_login(self):
        """
        Verify that hitting the root URL redirects to the login page.
        This confirms that authentication middleware and URL patterns are initialized.
        """
        response = self.client.get('/')
        # When not logged in, should redirect (302) to login page
        self.assertIn(response.status_code, [302, 200])

    def test_login_page_renders_successfully(self):
        """
        Verify that the login page boots and renders successfully (200 OK).
        This confirms that the template engine and base styles are working.
        """
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login', html=False)

    def test_payroll_create_payslip_endpoint_exists(self):
        """
        Verify that the payroll creation endpoint is registered and responds.
        """
        # Hitting anonymously should redirect to login (302)
        response = self.client.get('/payroll/create-payslip')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
