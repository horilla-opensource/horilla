from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from hydra_documents.scanning import _scan_with_clamd, scanner_health


class FakeSocket:
    def __init__(self, response):
        self.response = [response]
        self.sent = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, value):
        self.sent.extend(value)

    def recv(self, size):
        return self.response.pop(0) if self.response else b""


@override_settings(HYDRA_CLAMD_TIMEOUT_SECONDS=5)
class ClamdProtocolTests(SimpleTestCase):
    def test_clean_instream_response_is_parsed_and_file_is_rewound(self):
        sock = FakeSocket(b"stream: OK\0")
        source = BytesIO(b"safe content")

        with patch("hydra_documents.scanning._connect", return_value=sock):
            result = _scan_with_clamd(source)

        self.assertTrue(result.clean)
        self.assertEqual(result.scanner, "clamd")
        self.assertEqual(source.tell(), 0)
        self.assertTrue(sock.sent.startswith(b"zINSTREAM\0"))
        self.assertTrue(sock.sent.endswith(b"\x00\x00\x00\x00"))
        self.assertIn(b"safe content", sock.sent)

    def test_threat_name_is_parsed_without_treating_it_as_scanner_error(self):
        sock = FakeSocket(b"stream: Test.Signature FOUND\0")

        with patch("hydra_documents.scanning._connect", return_value=sock):
            result = _scan_with_clamd(BytesIO(b"content"))

        self.assertFalse(result.clean)
        self.assertEqual(result.result, "Test.Signature")

    @override_settings(HYDRA_DOCUMENT_SCANNER="clamd")
    def test_health_uses_framed_ping(self):
        sock = FakeSocket(b"PONG\0")

        with patch("hydra_documents.scanning._connect", return_value=sock):
            ok, detail = scanner_health()

        self.assertTrue(ok)
        self.assertIn("answered", detail)
        self.assertEqual(sock.sent, b"zPING\0")
