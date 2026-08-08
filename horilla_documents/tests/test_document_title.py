"""Document title validation smoke tests."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from horilla.testkit import make_company, make_employee
from horilla_documents.models import Document


class DocumentTitleTests(TestCase):
    def setUp(self):
        company = make_company("Docs Co")
        self.employee = make_employee(company=company, email="docs@test.horilla")

    def test_short_title_rejected(self):
        doc = Document(title="ab", employee_id=self.employee)
        with self.assertRaises(ValidationError):
            doc.clean()

    def test_valid_title_saves(self):
        doc = Document.objects.create(title="Passport", employee_id=self.employee)
        self.assertIsNotNone(doc.pk)
        self.assertEqual(doc.status, "requested")
