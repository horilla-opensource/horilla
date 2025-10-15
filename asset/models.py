"""
Models for Asset Management System

This module defines Django models to manage assets, their categories, assigning, and requests
within an Asset Management System.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla.models import HorillaModel, upload_path
from horilla_views.cbv_methods import render_template


class AssetCategory(HorillaModel):
    """
    Represents a category for different types of assets.
    """

    asset_category_name = models.CharField(
        max_length=255, unique=True, verbose_name=_("Name")
    )
    asset_category_description = models.TextField(
        max_length=255, verbose_name=_("Description")
    )
    objects = models.Manager()
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager("company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Asset Category")
        verbose_name_plural = _("Asset Categories")

    def __str__(self):
        return f"{self.asset_category_name}"


class AssetLot(HorillaModel):
    """
    Represents a lot associated with a collection of assets.
    """

    lot_number = models.CharField(
        max_length=30,
        null=False,
        blank=False,
        unique=True,
        verbose_name=_("Batch Number"),
    )
    lot_description = models.TextField(
        null=True, blank=True, verbose_name=_("Description")
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class to add additional options
        """

        ordering = ["-created_at"]
        verbose_name = _("Asset Batch")
        verbose_name_plural = _("Asset Batches")

    def __str__(self):
        return f"{self.lot_number}"

    def actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="cbv/asset_batch_no/actions.html",
            context={"instance": self},
        )

    def asset_batch_detail(self):
        """
        detail view
        """

        url = reverse("asset-batch-detail-view", kwargs={"pk": self.pk})

        return url

    def assets_column(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="cbv/asset_batch_no/assets_col.html",
            context={"instance": self},
        )

    def detail_actions(self):
        return render_template(
            path="cbv/asset_batch_no/detail_actions.html",
            context={"instance": self},
        )

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("asset-batch-update", kwargs={"pk": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("asset-batch-number-delete", kwargs={"batch_id": self.pk})
        return url


class Asset(HorillaModel):
    """
    Represents a asset with various attributes.
    """

    ASSET_STATUS = [
        ("In use", _("In Use")),
        ("Available", _("Available")),
        ("Not-Available", _("Not-Available")),
    ]
    asset_name = models.CharField(max_length=255, verbose_name=_("Asset Name"))
    owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Current User"),
    )
    asset_description = models.TextField(
        null=True, blank=True, max_length=255, verbose_name=_("Description")
    )
    asset_tracking_id = models.CharField(
        max_length=30, null=False, unique=True, verbose_name=_("Tracking Id")
    )
    asset_purchase_date = models.DateField(verbose_name=_("Purchase Date"))
    asset_purchase_cost = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Cost")
    )
    asset_category_id = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, verbose_name=_("Category")
    )
    asset_status = models.CharField(
        choices=ASSET_STATUS,
        default="Available",
        max_length=40,
        verbose_name=_("Status"),
    )
    asset_lot_number_id = models.ForeignKey(
        AssetLot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Batch No"),
    )
    expiry_date = models.DateField(null=True, blank=True, verbose_name=_("Expiry Date"))
    notify_before = models.IntegerField(
        default=1, null=True, verbose_name=_("Notify Before (days)")
    )
    objects = HorillaCompanyManager("asset_category_id__company_id")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Asset")
        verbose_name_plural = _("Assets")

    def __str__(self):
        return f"{self.asset_name}-{self.asset_tracking_id}"

    def action_column(self):
        """
        Action column for asset
        """
        return render_template(
            path="asset/action_column.html", context={"instance": self}
        )

    def detail_view_action(self):
        """
        This method for get custome coloumn .
        """

        return render_template(
            path="cbv/asset/detail_action.html",
            context={"instance": self},
        )

    def asset_detail(self):
        """
        detail view url
        """

        url = reverse_lazy("asset-information", kwargs={"pk": self.pk})
        return url

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("asset-update", kwargs={"pk": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("asset-delete", kwargs={"asset_id": self.pk})
        return url

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
    file = models.FileField(upload_to=upload_path, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        verbose_name = _("Asset Document")
        verbose_name_plural = _("Asset Documents")

    def __str__(self):
        return f"document for {self.asset_report}"


class ReturnImages(HorillaModel):
    """
    Model representing images associated with a returned asset.

    Attributes:
    - image: A FileField for uploading the image file (optional).
    """

    image = models.FileField(upload_to=upload_path, blank=True, null=True)


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
        Asset, on_delete=models.PROTECT, verbose_name=_("Asset")
    )
    assigned_to_employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="allocated_employee",
        verbose_name=_("Assigned To"),
    )
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by_employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="assigned_by",
        verbose_name=_("Assigned By"),
    )
    return_date = models.DateField(null=True, blank=True, verbose_name=_("Return Date"))
    return_condition = models.TextField(
        null=True, blank=True, verbose_name=_("Return Condition")
    )
    return_status = models.CharField(
        choices=STATUS,
        max_length=30,
        null=True,
        blank=True,
        verbose_name=_("Return Status"),
    )
    return_request = models.BooleanField(default=False)
    objects = HorillaCompanyManager("asset_id__asset_lot_number_id__company_id")
    return_images = models.ManyToManyField(
        ReturnImages, blank=True, related_name="return_images"
    )
    assign_images = models.ManyToManyField(
        ReturnImages,
        blank=True,
        related_name="assign_images",
        verbose_name=_("Assign Condition Images"),
    )
    objects = HorillaCompanyManager(
        "assigned_to_employee_id__employee_work_info__company_id"
    )

    class Meta:
        """Meta class for AssetAssignment model"""

        ordering = ["-id"]
        verbose_name = _("Asset Allocation")
        verbose_name_plural = _("Asset Allocations")

    def __str__(self):
        return f"{self.assigned_to_employee_id} --- {self.asset_id} --- {self.return_status}"

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.asset_id}&background=random"
        return url

    def asset_detail_view(self):
        """
        for detail view of page
        """
        url = reverse("asset-history-detail-view", kwargs={"pk": self.pk})
        return url

    def assign_condition_img(self):
        """
        This method for get custome coloumn .
        """

        return render_template(
            path="cbv/asset_history/assign_condition.html",
            context={"instance": self},
        )

    def return_condition_img(self):
        """
        This method for get custome coloumn .
        """

        return render_template(
            path="cbv/asset_history/return_condition.html",
            context={"instance": self},
        )

    def asset_action(self):
        """
        This method for get custom column for asset tab action.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_actions.html",
            context={"instance": self},
        )

    def return_status_col(self):
        """
        This method for get custom column for return date.
        """

        return render_template(
            path="cbv/request_and_allocation/return_status.html",
            context={"instance": self},
        )

    def allocation_action(self):
        """
        This method for get custom column for asset allocation tab actions.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_allocation_action.html",
            context={"instance": self},
        )

    def allocation_option(self):
        """
        This method for get custom column for asset tab action.
        """

        return render_template(
            path="cbv/request_and_allocation/allocation_option.html",
            context={"instance": self},
        )

    def asset_detail_action(self):
        """
        This method for get custom column for asset detail  actions.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_detail_action.html",
            context={"instance": self},
        )

    def asset_allocation_detail_action(self):
        """
        This method for get custom column for asset detail  actions.
        """

        return render_template(
            path="cbv/request_and_allocation/detail_action_asset_allocation.html",
            context={"instance": self},
        )

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the question template
        """
        url = f"https://ui-avatars.com/api/?name={self.asset_id.asset_name}&background=random"
        return url

    def detail_view_asset(self):
        """
        detail view
        """

        url = reverse("asset-detail-view", kwargs={"pk": self.pk})
        return url

    def detail_view_asset_allocation(self):
        """
        detail view
        """

        url = reverse("asset-allocation-detail-view", kwargs={"pk": self.pk})
        return url

    def asset_detail_status(self):
        """
        Asset tab detail status
        """

        return (
            '<span class="link-primary">Requested to return</span>'
            if self.return_request
            else '<span style = "color : yellowgreen;">In use</span>'
        )

    def detail_status(self):
        """
        Asset allocation  tab detail status
        """
        if self.return_date:
            status = '<span style = "color : red;" >Returned</span>'
        elif self.return_request:
            status = '<span class="link-primary">Requested to return</span>'
        else:
            status = '<span style = "color : yellowgreen;" >Allocated</span>'
        return status

    def asset_allocation_detail_subtitle(self):
        """
        Return subtitle containing both department and job position information.
        """
        return f"{self.assigned_to_employee_id.get_department()} / {self.assigned_to_employee_id.get_job_position()}"

    def status_display(self):
        status = self.asset_id.asset_status
        color_class = "oh-dot--warning"  # Adjust based on your status
        return format_html(
            '<span class="oh-dot oh-dot--small me-1 oh-dot--color {color_class}"></span>'
            '<span class="link-warning">{status}</span>',
            color_class=color_class,
            status=status,
        )

    def assigned_date_display(self):
        date_col = self.assigned_date
        color_class = "oh-dot--success"  # Adjust based on your status
        return format_html(
            '<span class="oh-dot oh-dot--small me-1 oh-dot--color {color_class}"></span>'
            '<span class="link-success dateformat_changer">{date_col}</span>',
            color_class=color_class,
            date_col=date_col,
        )

    def get_asset_of_offboarding_employee(self):
        url = f"{reverse('asset-request-allocation-view')}?assigned_to_employee_id={self.assigned_to_employee_id.id}"
        return url

    def get_send_mail_employee_link(self):
        if not self.assigned_to_employee_id:
            return ""
        url = reverse(
            "send-mail-employee", kwargs={"emp_id": self.assigned_to_employee_id.id}
        )
        title = _("Send Mail")
        html = f"""
        <a
            onclick="event.stopPropagation()"
            hx-get="{url}"
            data-toggle="oh-modal-toggle"
            data-target="#sendMailModal"
            title="{title}"
            hx-target="#mail-content"
        >
            <ion-icon name="mail-outline"></ion-icon>
        </a>
        """
        return format_html(html)


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
        verbose_name=_("Requesting User"),
    )
    asset_category_id = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, verbose_name=_("Asset Category")
    )
    asset_request_date = models.DateField(auto_now_add=True)
    description = models.TextField(
        null=True, blank=True, max_length=255, verbose_name=_("Description")
    )
    asset_request_status = models.CharField(
        max_length=30, choices=STATUS, default="Requested", null=True, blank=True
    )
    objects = HorillaCompanyManager(
        "requested_employee_id__employee_work_info__company_id"
    )

    class Meta:
        """Meta class for AssetRequest model"""

        ordering = ["-id"]
        verbose_name = _("Asset Request")
        verbose_name_plural = _("Asset Requests")

    def status_col(self):
        """
        This method for get custom coloumn for status.
        """

        return render_template(
            path="cbv/request_and_allocation/status.html",
            context={"instance": self},
        )

    def action_col(self):
        """
        This method for get custom coloumn for action.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_request_action.html",
            context={"instance": self},
        )

    def detail_action_col(self):
        """
        This method for get custom coloumn for detail action.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_request_detail_action.html",
            context={"instance": self},
        )

    def option_col(self):
        """
        This method for get custom coloumn for action.
        """

        return render_template(
            path="cbv/request_and_allocation/asset_request_option.html",
            context={"instance": self},
        )

    def asset_request_detail_subtitle(self):
        """
        Return subtitle containing both department and job position information.
        """
        return f"{self.requested_employee_id.get_department()} / {self.requested_employee_id.get_job_position()}"

    def detail_view_asset_request(self):
        """
        detail view
        """
        url = reverse("asset-request-detail-view", kwargs={"pk": self.pk})
        return url

    def status_html_class(self):
        COLOR_CLASS = {
            "Approved": "oh-dot--success",
            "Requested": "oh-dot--info",
            "Rejected": "oh-dot--danger",
        }

        LINK_CLASS = {
            "Approved": "link-success",
            "Requested": "link-info",
            "Rejected": "link-danger",
        }
        status = self.asset_request_status
        return {
            "color": COLOR_CLASS.get(status),
            "link": LINK_CLASS.get(status),
        }
