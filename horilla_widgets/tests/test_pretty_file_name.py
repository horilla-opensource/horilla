"""File widget display-name helper smoke tests."""

from django.test import SimpleTestCase

from horilla_widgets.widgets.file_widgets import pretty_file_name


class PrettyFileNameTests(SimpleTestCase):
    def test_strips_uuid_suffix(self):
        self.assertEqual(
            pretty_file_name("employee/document/file/passport-a1b2c3d4.pdf"),
            "passport.pdf",
        )

    def test_plain_basename(self):
        self.assertEqual(pretty_file_name("reports/summary.xlsx"), "summary.xlsx")
