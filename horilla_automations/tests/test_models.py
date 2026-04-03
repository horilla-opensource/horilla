"""
Tests for horilla_automations module models.

Covers MailAutomation CRUD, trigger/delivery choices, condition fields,
auto-generated method_title, and the CONDITIONS constant.
"""

from django.db import IntegrityError

from base.models import HorillaMailTemplate
from horilla.test_utils.base import HorillaTestCase
from horilla_automations.models import CONDITIONS, MailAutomation


# ---------------------------------------------------------------------------
# CONDITIONS Constant Tests
# ---------------------------------------------------------------------------
class ConditionsConstantTests(HorillaTestCase):
    """Tests for the CONDITIONS choices list."""

    def test_conditions_is_list_of_tuples(self):
        self.assertIsInstance(CONDITIONS, list)
        for item in CONDITIONS:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_conditions_contains_expected_operators(self):
        keys = [choice[0] for choice in CONDITIONS]
        self.assertIn("equal", keys)
        self.assertIn("notequal", keys)
        self.assertIn("lt", keys)
        self.assertIn("gt", keys)
        self.assertIn("le", keys)
        self.assertIn("ge", keys)
        self.assertIn("icontains", keys)


# ---------------------------------------------------------------------------
# MailAutomation Model Tests
# ---------------------------------------------------------------------------
class MailAutomationCreateTests(HorillaTestCase):
    """CRUD tests for MailAutomation."""

    def _make_automation(self, **kwargs):
        defaults = {
            "title": "Test Automation",
            "model": "employee.models.Employee",
            "mail_to": "['employee_id__email']",
            "mail_details": "instance",
            "trigger": "on_create",
            "condition": "{}",
            "condition_querystring": "",
            "delivery_channel": "email",
        }
        defaults.update(kwargs)
        return MailAutomation.objects.create(**defaults)

    def test_create_mail_automation(self):
        auto = self._make_automation()
        self.assertIsNotNone(auto.pk)
        self.assertEqual(auto.title, "Test Automation")

    def test_str_representation(self):
        auto = self._make_automation(title="Welcome Email")
        self.assertEqual(str(auto), "Welcome Email")

    def test_method_title_auto_generated_on_create(self):
        """method_title is auto-generated from title on first save."""
        auto = self._make_automation(title="New Employee Onboarding")
        self.assertEqual(auto.method_title, "new_employee_onboarding")

    def test_method_title_not_updated_on_subsequent_save(self):
        """method_title stays the same when title changes on update."""
        auto = self._make_automation(title="Original Title")
        original_method_title = auto.method_title
        auto.title = "Changed Title"
        auto.save()
        auto.refresh_from_db()
        self.assertEqual(auto.method_title, original_method_title)

    def test_title_unique(self):
        self._make_automation(title="Unique Automation")
        with self.assertRaises(IntegrityError):
            self._make_automation(title="Unique Automation")

    def test_trigger_choices_on_create(self):
        auto = self._make_automation(trigger="on_create")
        self.assertEqual(auto.trigger, "on_create")

    def test_trigger_choices_on_update(self):
        auto = self._make_automation(title="Update Auto", trigger="on_update")
        self.assertEqual(auto.trigger, "on_update")

    def test_trigger_choices_on_delete(self):
        auto = self._make_automation(title="Delete Auto", trigger="on_delete")
        self.assertEqual(auto.trigger, "on_delete")

    def test_trigger_display(self):
        auto = self._make_automation(trigger="on_create")
        self.assertEqual(auto.trigger_display(), "On Create")

    def test_delivery_channel_default_email(self):
        auto = self._make_automation()
        self.assertEqual(auto.delivery_channel, "email")

    def test_delivery_channel_notification(self):
        auto = self._make_automation(
            title="Notify Auto", delivery_channel="notification"
        )
        self.assertEqual(auto.delivery_channel, "notification")

    def test_delivery_channel_both(self):
        auto = self._make_automation(title="Both Auto", delivery_channel="both")
        self.assertEqual(auto.delivery_channel, "both")

    def test_send_options_complete(self):
        valid_channels = [choice[0] for choice in MailAutomation.SEND_OPTIONS]
        self.assertIn("email", valid_channels)
        self.assertIn("notification", valid_channels)
        self.assertIn("both", valid_channels)

    def test_mail_template_fk_nullable(self):
        auto = self._make_automation()
        self.assertIsNone(auto.mail_template)

    def test_mail_template_fk_set(self):
        template = HorillaMailTemplate.objects.create(
            title="Test Template",
            body="<p>Hello {{ employee }}</p>",
        )
        auto = self._make_automation(title="Template Auto", mail_template=template)
        self.assertEqual(auto.mail_template, template)

    def test_also_sent_to_m2m(self):
        auto = self._make_automation(title="CC Auto")
        auto.also_sent_to.add(self.manager_employee, self.regular_employee)
        self.assertEqual(auto.also_sent_to.count(), 2)

    def test_condition_field_stored(self):
        condition_str = '{"field": "status", "operator": "equal", "value": "active"}'
        auto = self._make_automation(title="Condition Auto", condition=condition_str)
        auto.refresh_from_db()
        self.assertEqual(auto.condition, condition_str)

    def test_xss_exempt_fields(self):
        """Verify XSS-exempt fields are declared correctly."""
        self.assertIn("condition_html", MailAutomation.xss_exempt_fields)
        self.assertIn("condition", MailAutomation.xss_exempt_fields)
        self.assertIn("condition_querystring", MailAutomation.xss_exempt_fields)

    def test_delete_mail_automation(self):
        auto = self._make_automation(title="To Delete")
        pk = auto.pk
        auto.delete()
        self.assertFalse(MailAutomation.objects.filter(pk=pk).exists())

    def test_update_mail_automation(self):
        auto = self._make_automation(title="To Update")
        auto.trigger = "on_update"
        auto.delivery_channel = "both"
        auto.save()
        auto.refresh_from_db()
        self.assertEqual(auto.trigger, "on_update")
        self.assertEqual(auto.delivery_channel, "both")

    def test_get_avatar_url(self):
        auto = self._make_automation(title="Avatar Test")
        url = auto.get_avatar()
        self.assertIn("ui-avatars.com", url)
        self.assertIn("Avatar Test", url)
