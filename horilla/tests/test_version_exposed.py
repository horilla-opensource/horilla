"""The running version must be readable from the UI.

`horilla/__version__.py` existed only for the build -- the Docker label and the
CI check that the tag matches it. Nothing showed it to the people running the
product, so "which version are you on?" could not be answered from the screen.
Support threads answered it with a branch name instead, which spans several
releases and cannot tell you whether a given security fix is present. That is
not hypothetical: 2.1.4 exists because 2.1.3 was vulnerable, and a user on
2.1.2 had no way to know they were missing the fixes.

The version is deliberately NOT added to /health/ or /ready/. Both are
unauthenticated and publicly reachable, and a version string there hands any
scanner the exact list of advisories that apply. That omission is load-bearing,
so it is asserted here rather than left to be "tidied up" later.
"""

from django.test import SimpleTestCase, TestCase

from base.context_processors import horilla_version
from horilla.__version__ import __version__


class VersionContextProcessorTests(SimpleTestCase):
    def test_it_reports_the_real_version(self):
        self.assertEqual(horilla_version(None), {"horilla_version": __version__})

    def test_it_is_registered(self):
        from django.conf import settings

        self.assertIn(
            "base.context_processors.horilla_version",
            settings.TEMPLATES[0]["OPTIONS"]["context_processors"],
        )


class VersionNotOnPublicProbesTests(TestCase):
    """These endpoints are public; keep the version off them."""

    def test_health_does_not_leak_the_version(self):
        body = self.client.get("/health/").content.decode()
        self.assertNotIn(__version__, body)

    def test_ready_does_not_leak_the_version(self):
        body = self.client.get("/ready/").content.decode()
        self.assertNotIn(__version__, body)
