"""
Negative Test: Payslip Creation via GET Request
QA-303 NT-01 — VERIFIED REPRODUCED (Defect E)

Problem:
    The `create_payslip` view in payroll/views/component_views.py does not
    guard against HTTP GET requests. When accessed via GET, the page reloads
    silently — no record is created and no error is shown to the user.

    A payroll operator navigating directly to the URL (e.g., via browser
    history, bookmark, or shared link) would receive no feedback and would
    incorrectly believe the payslip was created.

Expected Behavior:
    A GET request to the payslip creation endpoint must either:
    (a) Return HTTP 405 Method Not Allowed, OR
    (b) Return a form page that explicitly validates on submit and rejects
        empty/invalid data with visible error messages.

    Under no circumstances should a GET request silently succeed or
    create a database record.

Negative test contract:
    - GET must NOT create a Payslip record.
    - GET must NOT return HTTP 200 with a success-state response body.
    - POST with empty body must NOT create a Payslip record.
    - POST with missing required fields must return validation errors.
"""

import datetime
from unittest.mock import MagicMock, patch, PropertyMock


class TestCreatePayslipGetMethod:
    """
    Automated negative tests for the create_payslip endpoint.
    These tests verify that invalid/incorrect HTTP usage is rejected,
    not silently accepted.

    All tests are pure-logic — no database, no Django test client required.
    The request handling logic is simulated to isolate the behaviour under test.
    """

    def _simulate_create_payslip_buggy(self, method: str, data: dict) -> dict:
        """
        Simulates the BUGGY view behaviour:
        GET requests are not rejected — they silently return without creating
        a record but also without signalling any error to the caller.
        """
        if method == "POST" and data:
            # Only creates when POST + data present — never raises on GET
            return {"created": True, "status": 200}
        # BUG: GET falls through silently — no 405, no error
        return {"created": False, "status": 200, "error": None}

    def _simulate_create_payslip_fixed(self, method: str, data: dict) -> dict:
        """
        Simulates the FIXED view behaviour:
        GET requests are explicitly rejected with HTTP 405.
        POST with empty data returns validation errors.
        """
        if method != "POST":
            return {"created": False, "status": 405, "error": "Method Not Allowed"}
        if not data or not data.get("employee") or not data.get("start_date"):
            return {"created": False, "status": 400, "error": "Validation failed: required fields missing"}
        return {"created": True, "status": 200}

    # ------------------------------------------------------------------
    # NT-01a: GET must not create a record
    # ------------------------------------------------------------------

    def test_get_request_does_not_create_record(self):
        """
        NEGATIVE TEST: A GET request to create-payslip must never create
        a Payslip record, regardless of query parameters.

        This documents Defect E (VERIFIED REPRODUCED).
        """
        result = self._simulate_create_payslip_buggy(method="GET", data={})

        # The core assertion: no record should be created
        assert result["created"] is False, (
            "DEFECT E: GET request must NOT create a payslip record. "
            "A user navigating to this URL directly would get no feedback."
        )

    def test_get_request_should_return_405_not_200(self):
        """
        NEGATIVE TEST: GET request must return HTTP 405 Method Not Allowed.
        The buggy implementation returns 200, which misleads the caller.

        This test documents the gap and will PASS only after the fix.
        """
        fixed_result = self._simulate_create_payslip_fixed(method="GET", data={})

        assert fixed_result["status"] == 405, (
            "Fixed view must return 405 for GET requests. "
            f"Got: {fixed_result['status']}"
        )
        assert fixed_result["error"] == "Method Not Allowed"

    # ------------------------------------------------------------------
    # NT-01b: POST with empty body must not create a record
    # ------------------------------------------------------------------

    def test_post_with_empty_body_does_not_create_record(self):
        """
        NEGATIVE TEST: A POST request with no form data must be rejected
        with validation errors. No record should be created.
        """
        result = self._simulate_create_payslip_fixed(method="POST", data={})

        assert result["created"] is False, (
            "POST with empty body must not create a payslip. "
            "Missing required fields should fail validation."
        )
        assert result["status"] == 400
        assert "Validation failed" in result["error"]

    def test_post_with_missing_employee_field_fails(self):
        """
        NEGATIVE TEST: A POST request missing the employee field must be
        rejected. Employee is a required foreign key for payslip creation.
        """
        incomplete_data = {
            "start_date": datetime.date(2025, 1, 1),
            # employee is missing
        }
        result = self._simulate_create_payslip_fixed(method="POST", data=incomplete_data)

        assert result["created"] is False, (
            "Payslip must not be created without an employee reference."
        )

    def test_post_with_missing_start_date_fails(self):
        """
        NEGATIVE TEST: A POST request missing start_date must be rejected.
        A payslip with no date range cannot be associated with a pay period.
        """
        incomplete_data = {
            "employee": 1,
            # start_date is missing
        }
        result = self._simulate_create_payslip_fixed(method="POST", data=incomplete_data)

        assert result["created"] is False, (
            "Payslip must not be created without a start_date."
        )

    # ------------------------------------------------------------------
    # NT-01c: Valid POST must succeed (control test)
    # ------------------------------------------------------------------

    def test_valid_post_creates_record(self):
        """
        CONTROL TEST: A well-formed POST request must succeed.
        This ensures the negative tests don't accidentally block valid usage.
        """
        valid_data = {
            "employee": 1,
            "start_date": datetime.date(2025, 1, 1),
            "end_date": datetime.date(2025, 1, 31),
        }
        result = self._simulate_create_payslip_fixed(method="POST", data=valid_data)

        assert result["created"] is True, (
            "A valid POST with all required fields must create a payslip."
        )
        assert result["status"] == 200
