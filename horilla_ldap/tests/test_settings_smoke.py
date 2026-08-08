"""LDAP settings model smoke tests."""

from django.test import TestCase

from horilla_ldap.models import LDAPSettings


class LDAPSettingsSmokeTests(TestCase):
    def test_create_settings(self):
        settings = LDAPSettings.objects.create(bind_password="secret")
        self.assertIsNotNone(settings.pk)
        self.assertIn("ldap://", str(settings))
