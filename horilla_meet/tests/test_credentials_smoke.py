"""Google Meet credential helper smoke tests."""

from django.test import TestCase

from horilla.testkit import make_company
from horilla_meet.models import GoogleCloudCredential


class GoogleCredentialSmokeTests(TestCase):
    def test_redirect_uri_list(self):
        company = make_company("Meet Co")
        cred = GoogleCloudCredential.objects.create(
            client_id="cid",
            client_secret="csecret",
            redirect_uris="https://a.example/, https://b.example/",
            company_id=company,
        )
        self.assertEqual(
            cred.redirect_uri_list,
            ["https://a.example/", "https://b.example/"],
        )
