"""WhatsApp Meta URL helper smoke tests."""

from django.test import SimpleTestCase

from whatsapp.utils import get_meta_url


class GetMetaUrlTests(SimpleTestCase):
    def test_messages_url(self):
        self.assertEqual(
            get_meta_url("123", "messages"),
            "https://graph.facebook.com/v24.0/123/messages",
        )
