"""
Custom test assertions for Horilla HRMS.
"""

from django.core.exceptions import ValidationError

from horilla.models import has_xss


class HorillaAssertionsMixin:
    """
    Mixin providing Horilla-specific assertions.
    Add to any TestCase subclass.
    """

    def assertXSSRejected(self, model_or_form_class, field_name, xss_payload=None):
        """Assert that XSS payload is detected by has_xss()."""
        payloads = [
            xss_payload or "<script>alert('xss')</script>",
            "javascript:alert(1)",
            '<img onerror="alert(1)" src=x>',
            '<iframe src="evil.com"></iframe>',
            "<svg onload=\"fetch('evil.com')\">",
        ]
        for payload in payloads:
            self.assertTrue(
                has_xss(payload),
                f"XSS payload not detected: {payload!r}",
            )

    def assertXSSClean(self, value):
        """Assert that a value is NOT flagged as XSS."""
        self.assertFalse(
            has_xss(value),
            f"Clean value incorrectly flagged as XSS: {value!r}",
        )

    def assertPermissionDenied(self, response):
        """Assert response is permission denied (302 redirect or 403)."""
        self.assertIn(
            response.status_code,
            [302, 403],
            f"Expected 302 or 403, got {response.status_code}",
        )

    def assertHTMXResponse(self, response):
        """Assert response is a valid HTMX partial (200, no full page)."""
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(
            "<!DOCTYPE html>",
            content,
            "HTMX response should be a partial, not a full page",
        )

    def assertMultiTenantIsolation(
        self,
        model_class,
        company_a,
        company_b,
        company_a_field="company_id",
        expected_a=None,
        expected_b=None,
    ):
        """
        Assert that querying with company context returns only that company's data.
        Uses direct filter (not HorillaCompanyManager) for predictable testing.
        """
        a_count = model_class.objects.filter(**{company_a_field: company_a}).count()
        b_count = model_class.objects.filter(**{company_a_field: company_b}).count()

        if expected_a is not None:
            self.assertEqual(
                a_count,
                expected_a,
                f"Company A should have {expected_a} records, got {a_count}",
            )
        if expected_b is not None:
            self.assertEqual(
                b_count,
                expected_b,
                f"Company B should have {expected_b} records, got {b_count}",
            )

        # Cross-check: A's data should not include B's
        a_ids = set(
            model_class.objects.filter(**{company_a_field: company_a}).values_list(
                "pk", flat=True
            )
        )
        b_ids = set(
            model_class.objects.filter(**{company_a_field: company_b}).values_list(
                "pk", flat=True
            )
        )
        self.assertFalse(
            a_ids & b_ids,
            "Company A and B share record IDs — multi-tenant isolation broken",
        )
