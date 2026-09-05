"""
Rich-text fields were rendered with |safe, so the only guard against stored
XSS was the has_xss regex at write time -- a blocklist, not a parser. The
sanitize_html filter strips to an allow-list instead.
"""

from django.template import Context, Template
from django.test import TestCase

from base.templatetags.basefilters import sanitize_html


class SanitizeHtmlTests(TestCase):
    def test_formatting_is_preserved(self):
        html = "<p>Hello <b>world</b><br><ul><li>one</li></ul></p>"
        out = sanitize_html(html)
        for fragment in ("<p>", "<b>world</b>", "<br>", "<li>one</li>"):
            self.assertIn(fragment, out)

    def test_script_tag_removed(self):
        out = sanitize_html("<p>hi</p><script>alert(1)</script>")
        self.assertNotIn("<script", out)
        self.assertIn("<p>hi</p>", out)

    def test_event_handler_removed(self):
        self.assertNotIn("onerror", sanitize_html('<img src=x onerror=alert(1)>'))

    def test_javascript_url_removed(self):
        out = sanitize_html('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", out)

    def test_iframe_and_style_removed(self):
        out = sanitize_html('<iframe src="//evil"></iframe><style>x{}</style>')
        self.assertNotIn("<iframe", out)
        self.assertNotIn("<style", out)

    def test_safe_link_survives(self):
        out = sanitize_html('<a href="https://example.com" target="_blank">ok</a>')
        self.assertIn('href="https://example.com"', out)

    def test_empty_values(self):
        self.assertEqual(sanitize_html(None), "")
        self.assertEqual(sanitize_html(""), "")

    def test_filter_is_registered_and_marks_safe(self):
        """Rendered through the template engine, output must not be double-escaped."""
        rendered = Template(
            "{% load basefilters %}{{ value|sanitize_html }}"
        ).render(Context({"value": "<b>bold</b><script>x</script>"}))
        self.assertIn("<b>bold</b>", rendered)
        self.assertNotIn("&lt;b&gt;", rendered)
        self.assertNotIn("<script", rendered)
