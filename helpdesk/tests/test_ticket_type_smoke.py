"""Helpdesk ticket type smoke tests."""

from django.test import TestCase

from helpdesk.models import TicketType


class TicketTypeSmokeTests(TestCase):
    def test_create_ticket_type(self):
        tt = TicketType.objects.create(
            title="IT Support Unit",
            type="service_request",
            prefix="ITS",
        )
        self.assertIsNotNone(tt.pk)
        self.assertEqual(str(tt), "IT Support Unit")
