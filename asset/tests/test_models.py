"""
Tests for asset module models.

Covers AssetCategory, AssetLot, Asset, AssetAssignment, and AssetRequest
with CRUD, validation, and business logic tests.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from asset.models import (
    Asset,
    AssetAssignment,
    AssetCategory,
    AssetLot,
    AssetReport,
    AssetRequest,
)
from asset.tests.factories import (
    AssetAssignmentFactory,
    AssetCategoryFactory,
    AssetFactory,
    AssetLotFactory,
    AssetReportFactory,
    AssetRequestFactory,
)
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# AssetCategory Tests (~3)
# ---------------------------------------------------------------------------
class AssetCategoryTests(HorillaTestCase):
    """CRUD and validation tests for AssetCategory."""

    def test_create_category(self):
        cat = AssetCategoryFactory()
        self.assertIsNotNone(cat.pk)
        self.assertTrue(cat.asset_category_name)

    def test_str_representation(self):
        cat = AssetCategoryFactory(asset_category_name="Laptops")
        self.assertEqual(str(cat), "Laptops")

    def test_category_name_unique(self):
        AssetCategoryFactory(asset_category_name="Monitors")
        with self.assertRaises(IntegrityError):
            AssetCategoryFactory(asset_category_name="Monitors")

    def test_category_with_company(self):
        cat = AssetCategoryFactory(company_id=[self.company_a])
        self.assertIn(self.company_a, cat.company_id.all())


# ---------------------------------------------------------------------------
# AssetLot Tests (~4)
# ---------------------------------------------------------------------------
class AssetLotTests(HorillaTestCase):
    """CRUD and validation tests for AssetLot."""

    def test_create_lot(self):
        lot = AssetLotFactory()
        self.assertIsNotNone(lot.pk)

    def test_str_representation(self):
        lot = AssetLotFactory(lot_number="BATCH-001")
        self.assertEqual(str(lot), "BATCH-001")

    def test_lot_number_unique(self):
        AssetLotFactory(lot_number="BATCH-UNIQUE")
        with self.assertRaises(IntegrityError):
            AssetLotFactory(lot_number="BATCH-UNIQUE")

    def test_lot_with_description(self):
        lot = AssetLotFactory(lot_description="Q1 2026 laptop batch")
        self.assertEqual(lot.lot_description, "Q1 2026 laptop batch")


# ---------------------------------------------------------------------------
# Asset Tests (~5)
# ---------------------------------------------------------------------------
class AssetTests(HorillaTestCase):
    """CRUD and validation tests for Asset."""

    def test_create_asset(self):
        asset = AssetFactory()
        self.assertIsNotNone(asset.pk)

    def test_str_representation(self):
        asset = AssetFactory(asset_name="MacBook Pro", asset_tracking_id="MBP-001")
        self.assertEqual(str(asset), "MacBook Pro-MBP-001")

    def test_asset_status_choices(self):
        for status_val, _ in Asset.ASSET_STATUS:
            asset = AssetFactory(asset_status=status_val)
            self.assertEqual(asset.asset_status, status_val)

    def test_default_status_available(self):
        asset = AssetFactory()
        self.assertEqual(asset.asset_status, "Available")

    def test_tracking_id_unique(self):
        AssetFactory(asset_tracking_id="UNIQUE-TRK-001")
        with self.assertRaises(IntegrityError):
            AssetFactory(asset_tracking_id="UNIQUE-TRK-001")

    def test_category_fk(self):
        cat = AssetCategoryFactory(asset_category_name="Keyboards")
        asset = AssetFactory(asset_category_id=cat)
        self.assertEqual(asset.asset_category_id, cat)

    def test_lot_fk(self):
        lot = AssetLotFactory(lot_number="LOT-FK-TEST")
        asset = AssetFactory(asset_lot_number_id=lot)
        self.assertEqual(asset.asset_lot_number_id, lot)

    def test_clean_duplicate_tracking_id_raises(self):
        """Asset.clean() should raise ValidationError for duplicate tracking IDs."""
        AssetFactory(asset_tracking_id="DUP-CLEAN-001")
        asset2 = AssetFactory(asset_tracking_id="DUP-CLEAN-TEMP")
        asset2.asset_tracking_id = "DUP-CLEAN-001"
        with self.assertRaises(ValidationError):
            asset2.clean()


# ---------------------------------------------------------------------------
# AssetAssignment Tests (~4)
# ---------------------------------------------------------------------------
class AssetAssignmentTests(HorillaTestCase):
    """CRUD and validation tests for AssetAssignment."""

    def test_create_assignment(self):
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
        )
        self.assertIsNotNone(assignment.pk)
        self.assertEqual(assignment.assigned_to_employee_id, self.regular_employee)
        self.assertEqual(assignment.assigned_by_employee_id, self.manager_employee)

    def test_str_representation(self):
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
        )
        result = str(assignment)
        self.assertIn("---", result)

    def test_assigned_date_auto_set(self):
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
        )
        self.assertIsNotNone(assignment.assigned_date)
        self.assertEqual(assignment.assigned_date, date.today())

    def test_return_date_nullable(self):
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
        )
        self.assertIsNone(assignment.return_date)

    def test_return_status_choices(self):
        for status_val, _ in AssetAssignment.STATUS:
            assignment = AssetAssignmentFactory(
                return_status=status_val,
            )
            self.assertEqual(assignment.return_status, status_val)

    def test_detail_status_allocated(self):
        """When no return_date and no return_request, status should show Allocated."""
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
            return_date=None,
            return_request=False,
        )
        status_html = assignment.detail_status()
        self.assertIn("Allocated", str(status_html))

    def test_detail_status_returned(self):
        """When return_date is set, status should show Returned."""
        assignment = AssetAssignmentFactory(
            assigned_to_employee_id=self.regular_employee,
            assigned_by_employee_id=self.manager_employee,
            return_date=date.today(),
        )
        status_html = assignment.detail_status()
        self.assertIn("Returned", str(status_html))


# ---------------------------------------------------------------------------
# AssetRequest Tests (~4)
# ---------------------------------------------------------------------------
class AssetRequestTests(HorillaTestCase):
    """CRUD and validation tests for AssetRequest."""

    def test_create_request(self):
        req = AssetRequestFactory(requested_employee_id=self.regular_employee)
        self.assertIsNotNone(req.pk)
        self.assertEqual(req.requested_employee_id, self.regular_employee)

    def test_default_status_requested(self):
        req = AssetRequestFactory()
        self.assertEqual(req.asset_request_status, "Requested")

    def test_status_choices(self):
        for status_val, _ in AssetRequest.STATUS:
            req = AssetRequestFactory(asset_request_status=status_val)
            self.assertEqual(req.asset_request_status, status_val)

    def test_request_date_auto_set(self):
        req = AssetRequestFactory()
        self.assertIsNotNone(req.asset_request_date)
        self.assertEqual(req.asset_request_date, date.today())

    def test_category_fk(self):
        cat = AssetCategoryFactory(asset_category_name="Desks")
        req = AssetRequestFactory(asset_category_id=cat)
        self.assertEqual(req.asset_category_id, cat)

    def test_status_html_class(self):
        req_approved = AssetRequestFactory(asset_request_status="Approved")
        classes = req_approved.status_html_class()
        self.assertEqual(classes["color"], "oh-dot--success")
        self.assertEqual(classes["link"], "link-success")

        req_rejected = AssetRequestFactory(asset_request_status="Rejected")
        classes = req_rejected.status_html_class()
        self.assertEqual(classes["color"], "oh-dot--danger")
        self.assertEqual(classes["link"], "link-danger")

        req_requested = AssetRequestFactory(asset_request_status="Requested")
        classes = req_requested.status_html_class()
        self.assertEqual(classes["color"], "oh-dot--info")
        self.assertEqual(classes["link"], "link-info")


# ---------------------------------------------------------------------------
# AssetReport Tests (~2)
# ---------------------------------------------------------------------------
class AssetReportTests(HorillaTestCase):
    """Tests for AssetReport model."""

    def test_str_with_title(self):
        asset = AssetFactory(asset_name="Monitor", asset_tracking_id="MON-001")
        report = AssetReportFactory(title="Damage Report", asset_id=asset)
        self.assertEqual(str(report), f"{asset} - Damage Report")

    def test_str_without_title(self):
        asset = AssetFactory(asset_name="Monitor", asset_tracking_id="MON-002")
        report = AssetReportFactory(title=None, asset_id=asset)
        self.assertEqual(str(report), f"report for {asset}")
