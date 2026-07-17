from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from hydra_shell.checks import check_public_portal_url
from hydra_shell.links import public_portal_url
from hydra_shell.templatetags.hydra_shell_tags import hydra_nav_is_active


class PublicPortalLinkTests(SimpleTestCase):
    def test_link_maps_ukrainian_and_drops_untrusted_query_data(self):
        url = public_portal_url(
            base_url="https://portal.example.test/start?person=123&token=secret#private",
            language_code="uk-UA",
        )
        parts = urlsplit(url)

        self.assertEqual(parts.scheme, "https")
        self.assertEqual(parts.netloc, "portal.example.test")
        self.assertEqual(parts.path, "/start")
        self.assertEqual(parse_qs(parts.query), {"lang": ["ua"], "from": ["hydra"]})
        self.assertEqual(parts.fragment, "")

    def test_unsupported_language_falls_back_to_russian(self):
        url = public_portal_url(
            base_url="https://portal.example.test/",
            language_code="de",
        )

        self.assertEqual(parse_qs(urlsplit(url).query)["lang"], ["ru"])

    def test_insecure_or_relative_portal_url_is_rejected(self):
        for base_url in ("http://portal.example.test/", "/relative/"):
            with self.subTest(base_url=base_url):
                with self.assertRaises(ImproperlyConfigured):
                    public_portal_url(base_url=base_url, language_code="pl")

    @override_settings(HYDRA_PORTAL_URL="http://portal.example.test/")
    def test_django_system_check_reports_insecure_configuration(self):
        errors = check_public_portal_url(None)

        self.assertEqual([error.id for error in errors], ["hydra_shell.E001"])


class ShellNavigationTagTests(SimpleTestCase):
    def context_for(self, url_name):
        return {
            "request": SimpleNamespace(
                resolver_match=SimpleNamespace(url_name=url_name)
            )
        }

    def test_people_recruitment_and_organization_routes_activate_correct_modules(self):
        self.assertTrue(
            hydra_nav_is_active(self.context_for("hydra-person-detail"), "people")
        )
        self.assertFalse(
            hydra_nav_is_active(
                self.context_for("hydra-person-detail"), "organization"
            )
        )
        self.assertTrue(
            hydra_nav_is_active(
                self.context_for("hydra-person-assign"), "organization"
            )
        )
        self.assertFalse(
            hydra_nav_is_active(self.context_for("hydra-person-assign"), "people")
        )
        self.assertTrue(
            hydra_nav_is_active(
                self.context_for("hydra-recruitment-detail"), "recruitment"
            )
        )
        self.assertFalse(
            hydra_nav_is_active(
                self.context_for("hydra-recruitment-detail"), "people"
            )
        )
        for url_name in (
            "hydra-private-document-type-list",
            "hydra-private-document-type-create",
            "hydra-private-document-type-update",
        ):
            with self.subTest(url_name=url_name):
                self.assertTrue(
                    hydra_nav_is_active(self.context_for(url_name), "recruitment")
                )
        for url_name in (
            "hydra-duplicate-list",
            "hydra-duplicate-detail",
            "hydra-duplicate-preview",
            "hydra-duplicate-commit",
            "hydra-duplicate-dismiss",
        ):
            with self.subTest(url_name=url_name):
                self.assertTrue(
                    hydra_nav_is_active(self.context_for(url_name), "people")
                )
