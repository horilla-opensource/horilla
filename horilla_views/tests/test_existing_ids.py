"""The list's selection store keeps ids of deleted records; this endpoint tells
the browser which selected ids still exist so it can drop the rest."""

import json

from django.test import Client, TestCase
from django.urls import reverse

from horilla.testkit import make_company, make_employee, make_user


class ExistingIdsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Existing Ids Co")
        cls.user = make_user("ids-admin", is_superuser=True)
        cls.admin = make_employee(
            company=company, email="ids-admin@test.horilla", user=cls.user
        )
        cls.other = make_employee(company=company, email="ids-other@test.horilla")

    def _post(self, **data):
        client = Client()
        client.force_login(self.user)
        return client.post(reverse("hlv-existing-ids"), data)

    def test_returns_only_ids_that_still_exist(self):
        gone = self.other.pk + 1000
        response = self._post(
            model="employee.employee",
            ids=json.dumps([self.admin.pk, self.other.pk, gone]),
        )
        self.assertEqual(
            sorted(response.json()["ids"]),
            sorted([str(self.admin.pk), str(self.other.pk)]),
        )

    def test_unknown_model_is_a_bad_request(self):
        self.assertEqual(self._post(model="nope.nope", ids="[1]").status_code, 400)

    def test_anonymous_user_is_refused(self):
        response = Client().post(
            reverse("hlv-existing-ids"), {"model": "employee.employee", "ids": "[1]"}
        )
        self.assertNotEqual(response.status_code, 200)

    def test_bad_ids_are_a_bad_request(self):
        self.assertEqual(
            self._post(model="employee.employee", ids='["abc"]').status_code, 400
        )


class BulkDeleteWiringTests(TestCase):
    """The browser-side registry must only name real models, and the middleware
    must drop the toasts of requests the browser reports itself."""

    def test_every_registered_model_exists(self):
        import re

        from django.apps import apps

        js = open("static/index/index.js", encoding="utf-8").read()
        block = js[js.index("var HLV_BULK_DELETE_MODELS") :]
        block = block[: block.index("};")]
        labels = re.findall(r'"[a-z-]+": "([a-z_]+\.[a-z_]+)"', block)
        self.assertGreater(len(labels), 20)
        for label in labels:
            try:
                apps.get_model(label)
            except LookupError:
                if label.split(".")[0] in {"biometric", "project", "pms", "helpdesk"}:
                    continue  # optional app, not installed in every deployment
                self.fail(f"{label} in HLV_BULK_DELETE_MODELS is not a model")

    def test_middleware_discards_messages_for_bulk_delete_requests(self):
        from django.contrib import messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.http import HttpResponse
        from django.test import RequestFactory

        from horilla.horilla_middlewares import BulkDeleteSummaryMiddleware

        def view(request):
            messages.error(request, "You cannot delete X.")
            return HttpResponse("ok")

        for header, expected in (({"HTTP_X_HLV_BULK_DELETE": "1"}, 0), ({}, 1)):
            request = RequestFactory().post("/x/", **header)
            request.session = {}
            request._messages = FallbackStorage(request)
            BulkDeleteSummaryMiddleware(view)(request)
            self.assertEqual(len(request._messages._queued_messages), expected)
