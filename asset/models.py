"""
Models for Asset Management System

This module defines Django models to manage assets, their categories, assigning, and requests
within an Asset Management System.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla.models import HorillaModel


class AssetCategory(HorillaModel):
    """
    Represents a category for different types of assets.
    """

    asset_category_name = models.CharField(max_length=255, unique=True)
    asset_category_description = models.TextField(max_length=255)
    objects = models.Manager()
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    def __str__(self):
        return f"{self.asset_category_name}"


class AssetLot(HorillaModel):
    """
    Represents a lot associated with a collection of assets.
    """

    lot_number = models.CharField(max_length=30, null=False, blank=False, unique=True)
    lot_description = models.TextField(null=True, blank=True, max_length=255)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    def __str__(self):
        return f"{self.lot_number}"


class Asset(HorillaModel):
    """
    Represents a asset with various attributes.
    """

    ASSET_STATUS = [
        ("In use", _("In Use")),
        ("Available", _("Available")),
        ("Not-Available", _("Not-Available")),
    ]
    asset_name = models.CharField(max_length=255)
    owner = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True)
    asset_description = models.TextField(null=True, blank=True, max_length=255)
    asset_tracking_id = models.CharField(max_length=30, null=False, unique=True)
    asset_purchase_date = models.DateField()
    asset_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2)
    asset_category_id = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    asset_status = models.CharField(
        choices=ASSET_STATUS, default="Available", max_length=40
    )
    asset_lot_number_id = models.ForeignKey(
        AssetLot, on_delete=models.PROTECT, null=True, blank=True
    )
    expiry_date = models.DateField(null=True, blank=True)
    notify_before = models.IntegerField(default=1, null=True)
    objects = HorillaCompanyManager("asset_category_id__company_id")

    def __str__(self):
        return f"{self.asset_name}-{self.asset_tracking_id}"

    def clean(self):
        existing_asset = Asset.objects.filter(
            asset_tracking_id=self.asset_tracking_id
        ).exclude(
            id=self.pk
        )  # Exclude the current instance if updating
        if existing_asset.exists():
            raise ValidationError(
                {
                    "asset_description": _(
                        "An asset with this tracking ID already exists."
                    )
                }
            )
        return super().clean()


class AssetReport(HorillaModel):
    """
    Model representing a report for an asset.

    Attributes:
    - title: A CharField for the title of the report (optional).
    - asset_id: A ForeignKey to the Asset model, linking the report to a specific asset.
    """

    title = models.CharField(max_length=255, blank=True, null=True)
    asset_id = models.ForeignKey(
        Asset, related_name="asset_report", on_delete=models.CASCADE
    )

    def __str__(self):
        """
        Returns a string representation of the AssetReport instance.
        If a title is present, it returns "asset_id - title".
        Otherwise, it returns "report for asset_id".
        """
        return (
            f"{self.asset_id} - {self.title}"
            if self.title
            else f"report for {self.asset_id}"
        )


class AssetDocuments(HorillaModel):
    """
    Model representing documents associated with an asset report.

    Attributes:
    - asset_report: A ForeignKey to the AssetReport model, linking the document to
    a specific asset report.
    - file: A FileField for uploading the document file (optional).
    """

    asset_report = models.ForeignKey(
        "AssetReport", related_name="documents", on_delete=models.CASCADE
    )
    file = models.FileField(
        upload_to="asset/asset_report/documents/", blank=True, null=True
    )
    objects = models.Manager()

    def __str__(self):
        return f"document for {self.asset_report}"


class ReturnImages(HorillaModel):
    """
    Model representing images associated with a returned asset.

    Attributes:
    - image: A FileField for uploading the image file (optional).
    """

    image = models.FileField(upload_to="asset/return_images/", blank=True, null=True)


class AssetAssignment(HorillaModel):
    """
    Represents the allocation and return of assets to and from employees.
    """

    STATUS = [
        ("Minor damage", _("Minor damage")),
        ("Major damage", _("Major damage")),
        ("Healthy", _("Healthy")),
    ]
    asset_id = models.ForeignKey(
        Asset, on_delete=models.PROTECT, verbose_name=_("asset")
    )
    assigned_to_employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="allocated_employee"
    )
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by_employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assigned_by"
    )
    return_date = models.DateField(null=True, blank=True)
    return_condition = models.TextField(null=True, blank=True, max_length=255)
    return_status = models.CharField(
        choices=STATUS, max_length=30, null=True, blank=True
    )
    return_request = models.BooleanField(default=False)
    objects = HorillaCompanyManager("asset_id__asset_lot_number_id__company_id")
    return_images = models.ManyToManyField(
        ReturnImages, blank=True, related_name="return_images"
    )
    assign_images = models.ManyToManyField(
        ReturnImages, blank=True, related_name="assign_images"
    )

    class Meta:
        """Meta class for AssetAssignment model"""

        ordering = ["-id"]

    def __str__(self):
        return f"{self.assigned_to_employee_id} --- {self.asset_id} --- {self.return_status}"


class AssetRequest(HorillaModel):
    """
    Represents a request for assets made by employees.
    """

    STATUS = [
        ("Requested", _("Requested")),
        ("Approved", _("Approved")),
        ("Rejected", _("Rejected")),
    ]
    requested_employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="requested_employee",
        null=False,
        blank=False,
    )
    asset_category_id = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, verbose_name=_("Asset Category")
    )
    asset_request_date = models.DateField(auto_now_add=True)
    description = models.TextField(null=True, blank=True, max_length=255)
    asset_request_status = models.CharField(
        max_length=30, choices=STATUS, default="Requested", null=True, blank=True
    )
    objects = HorillaCompanyManager(
        "requested_employee_id__employee_work_info__company_id"
    )

    class Meta:
        """Meta class for AssetRequest model"""

        ordering = ["-id"]
