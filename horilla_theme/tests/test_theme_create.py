"""Theme model smoke tests."""

from django.core.validators import RegexValidator
from django.test import SimpleTestCase, TestCase

from horilla_theme.models import THEMES_DATA, HorillaColorTheme


class ThemeCreateTests(TestCase):
    def test_create_from_theme_data(self):
        data = dict(THEMES_DATA[1])
        data["name"] = "Unit Smoke Ocean Theme"
        data["is_default"] = False
        theme = HorillaColorTheme.objects.create(**data)
        self.assertIsNotNone(theme.pk)
        self.assertEqual(theme.primary_600, "#3b82f6")


class ThemeHexValidatorTests(SimpleTestCase):
    def test_hex_validator_rejects_invalid(self):
        validator = RegexValidator(r"^#[0-9A-Fa-f]{6}$")
        with self.assertRaises(Exception):
            validator("#GGGGGG")
