"""Deleting a document over the API must check who is asking.

GHSA-x72c-5gf7-97g3 reported that ``DELETE /api/employee/documents/<pk>/`` let
any authenticated employee destroy any other employee's uploaded documents --
contracts, identity documents, certificates -- by numeric id.

Two things had to line up. ``get_object`` took ``request`` as an optional
argument and ran its authorization check only when one was passed; ``delete``
did not pass it. The remaining guard was an ``owner_can_enter`` decorator
configured with ``model=Employee`` while the pk in the URL is a Document id, so
it resolved an employee from a document id and, finding none, took its
``or not employee`` branch and allowed the call.

The fix makes ``request`` required rather than patching the one caller that
forgot it: an optional argument that silently disables an authorization check
will be forgotten again.

``test_owner_is_not_refused_when_ids_collide`` covers the other half of the
misconfiguration, which the report does not mention. When a document id happens
to match some employee id, the decorator authorized against that unrelated
employee -- so it could refuse the document's actual owner. The same defect
denied legitimate access as well as granting illegitimate access.
"""

from django.core.files.base import ContentFile
from django.test import TestCase
from rest_framework.test import APIClient

from horilla.testkit import make_company, make_employee, make_user
from horilla_documents.models import Document, DocumentRequest

ENDPOINT = "/api/employee/documents/{}/"


class DocumentApiAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = make_company("Doc Co")

        self.attacker_user = make_user("doc_attacker", password="secret123")
        self.attacker = make_employee(
            company=company,
            email="doc_attacker@test.horilla",
            user=self.attacker_user,
            phone="2000001",
        )
        self.victim_user = make_user("doc_victim", password="secret123")
        self.victim = make_employee(
            company=company,
            email="doc_victim@test.horilla",
            user=self.victim_user,
            phone="2000002",
        )

        self.request = DocumentRequest.objects.create(title="req")
        self.request.employee_id.add(self.victim)

    def _document(self, owner=None):
        doc = Document.objects.create(
            title="contract",
            employee_id=owner or self.victim,
            document_request_id=self.request,
        )
        doc.document.save("contract.txt", ContentFile(b"x"), save=True)
        return doc

    def _auth(self, user):
        self.client.force_authenticate(user=type(user).objects.get(pk=user.pk))

    def test_stranger_cannot_delete_another_employees_document(self):
        """The reported attack. The document must survive it."""
        doc = self._document()
        self._auth(self.attacker_user)
        response = self.client.delete(ENDPOINT.format(doc.pk))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(pk=doc.pk).exists())

    def test_stranger_cannot_delete_even_when_id_is_past_the_employee_range(self):
        """
        The original exploit needed a document id higher than every employee id,
        which is the steady state once an install has more documents than
        people. Create enough documents to reach that range and confirm the
        delete is refused there too.
        """
        docs = [self._document() for _ in range(6)]
        target = docs[-1]
        self.assertGreater(target.pk, self.victim.pk)
        self._auth(self.attacker_user)
        response = self.client.delete(ENDPOINT.format(target.pk))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(pk=target.pk).exists())

    def test_stranger_cannot_read_or_overwrite_another_employees_document(self):
        doc = self._document()
        self._auth(self.attacker_user)
        self.assertEqual(self.client.get(ENDPOINT.format(doc.pk)).status_code, 403)
        response = self.client.put(
            ENDPOINT.format(doc.pk), {"title": "overwritten"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Document.objects.get(pk=doc.pk).title, "contract")

    def test_owner_can_still_delete_their_own_document(self):
        doc = self._document()
        self._auth(self.victim_user)
        response = self.client.delete(ENDPOINT.format(doc.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())

    def test_owner_is_not_refused_when_ids_collide(self):
        """
        Not in the report: the misconfigured decorator resolved an Employee from
        a Document id, so a document whose id matched an unrelated employee's id
        was authorized against that stranger and the real owner was refused.
        """
        # Pin the document id to the attacker's employee id rather than hoping
        # two independent sequences happen to meet. Waiting for a natural
        # collision made this skip, and a skipped test asserts nothing.
        #
        # Adding an employee to a DocumentRequest already creates their Document
        # row, so the low ids are taken; reuse that row when it is the one we
        # need instead of inserting over it.
        doc = Document.objects.filter(pk=self.attacker.pk).first()
        if doc is None:
            doc = Document.objects.create(
                id=self.attacker.pk,
                title="contract",
                employee_id=self.victim,
                document_request_id=self.request,
            )
        else:
            doc.employee_id = self.victim
            doc.save()
        doc.document.save("contract.txt", ContentFile(b"x"), save=True)
        self.assertEqual(doc.pk, self.attacker.pk)
        self.assertEqual(doc.employee_id, self.victim)

        self._auth(self.victim_user)
        response = self.client.delete(ENDPOINT.format(doc.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())
