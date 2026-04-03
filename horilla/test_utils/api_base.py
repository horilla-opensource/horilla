"""
DRF API test base class for Horilla HRMS.
"""

from rest_framework.test import APIClient, APITestCase

from horilla.test_utils.base import HorillaTestCase


class HorillaAPITestCase(HorillaTestCase, APITestCase):
    """
    Base test class for DRF API tests.

    Inherits HorillaTestCase fixtures and adds:
    - APIClient with force_authenticate helpers
    - JWT token creation helpers
    """

    def get_api_client(self, user=None):
        """Return an APIClient authenticated as the given user."""
        client = APIClient()
        if user:
            client.force_authenticate(user=user)
        return client

    def get_admin_api_client(self):
        return self.get_api_client(self.admin_user)

    def get_manager_api_client(self):
        return self.get_api_client(self.manager_user)

    def get_employee_api_client(self):
        return self.get_api_client(self.regular_user)

    def get_anonymous_api_client(self):
        return self.get_api_client()
