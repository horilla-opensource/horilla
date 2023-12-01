"""
Models for Asset Management System

This module defines Django models to manage assets, their categories, assigning, and requests
within an Asset Management System.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from base.models import Company
from base.horilla_company_manager import HorillaCompanyManager
from employee.models import Employee


class AssetCategory(models.Model):
    """
    Represents a category for different types of assets.
    """

    asset_category_name = models.CharField(max_length=255, unique=True)
    asset_category_description = models.TextField()
    objects = models.Manager()
    company_id = models.ManyToManyField(Company,blank=True, verbose_name=_("Company"))

    def __str__(self):
        return f"{self.asset_category_name}"


class AssetLot(models.Model):
    """
    Represents a lot associated with a collection of assets.
    """

    lot_number = models.CharField(max_length=30, null=False, blank=False, unique=True)
    lot_description = models.TextField(null=True, blank=True)
    company_id = models.ManyToManyField(Company,blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    def __str__(self):
        return f"{self.lot_number}"


class Asset(models.Model):
    """
    Represents a asset with various attributes.
    """

    ASSET_STATUS = [
        ("In use", _("In use")),
        ("Available", _("Available")),
        ("Not-Available", _("Not-Available")),
    ]
    asset_name = models.CharField(max_length=255)
    asset_description = models.TextField(null=True, blank=True)
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


class AssetAssignment(models.Model):
    """
    Represents the allocation and return of assets to and from employees.
    """

    STATUS = [
        ("Minor damage", _("Minor damage")),
        ("Major damage", _("Major damage")),
        ("Healthy", _("Healthy")),
    ]
    asset_id = models.ForeignKey(
        Asset, on_delete=models.PROTECT,
    )
    assigned_to_employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="allocated_employeee"
    )
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by_employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assigned_by"
    )
    return_date = models.DateField(null=True, blank=True)
    return_condition = models.TextField(null=True, blank=True)
    return_status = models.CharField(
        choices=STATUS, max_length=30, null=True, blank=True
    )
    objects = HorillaCompanyManager("asset_id__asset_lot_number_id__company_id")


class AssetRequest(models.Model):
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
    asset_category_id = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    asset_request_date = models.DateField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    asset_request_status = models.CharField(
        max_length=30, choices=STATUS, default="Requested", null=True, blank=True
    )
    objects = HorillaCompanyManager("requested_employee_id__employee_work_info__company_id")
