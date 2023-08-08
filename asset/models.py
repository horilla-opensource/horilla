from django.db import models
from django.contrib.auth.models import User
from employee.models import Employee
from datetime import datetime
import django
from django.utils.translation import gettext_lazy as _


class AssetCategory(models.Model):
    asset_category_name = models.CharField(max_length=255, unique=True)
    asset_category_description = models.TextField()

    def __str__(self):
        return f"{self.asset_category_name}"


class AssetLot(models.Model):
    lot_number = models.CharField(max_length=30, null=False, blank=False, unique=True)
    lot_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.lot_number}"


class Asset(models.Model):
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
    asset_category_id = models.ForeignKey(AssetCategory, on_delete=models.CASCADE)
    asset_status = models.CharField(
        choices=ASSET_STATUS, default="Available", max_length=40
    )
    asset_lot_number_id = models.ForeignKey(
        AssetLot, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.asset_name}-{self.asset_tracking_id}"


class AssetAssignment(models.Model):
    STATUS = [
        ("Minor damage", _("Minor damage")),
        ("Major damage", _("Major damage")),
        ("Healthy", _("Healthy")),
    ]
    asset_id = models.ForeignKey(
        Asset, on_delete=models.CASCADE, limit_choices_to={"asset_status": "Available"}
    )
    assigned_to_employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="allocated_employeee"
    )
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by_employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="assigned_by"
    )
    return_date = models.DateField(null=True, blank=True)
    return_condition = models.TextField(null=True, blank=True)
    return_status = models.CharField(
        choices=STATUS, max_length=30, null=True, blank=True
    )


class AssetRequest(models.Model):
    STATUS = [
        ("Requested", _("Requested")),
        ("Approved", _("Approved")),
        ("Rejected", _("Rejected")),
    ]
    requested_employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="requested_employee",
        null=False,
        blank=False,
    )
    asset_category_id = models.ForeignKey(AssetCategory, on_delete=models.CASCADE)
    asset_request_date = models.DateField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    asset_request_status = models.CharField(
        max_length=30, choices=STATUS, default="Requested", null=True, blank=True
    )
