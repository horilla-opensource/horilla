import os
from datetime import date

from django.apps import apps
from django.db import models
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.forms import ValidationError
from django.utils.translation import gettext as _

from base.horilla_company_manager import HorillaCompanyManager
from employee.models import Employee
from horilla.models import HorillaModel, upload_path

STATUS = [
    ("requested", "Requested"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]
FORMATS = [
    ("any", "Any"),
    ("pdf", "PDF"),
    ("txt", "TXT"),
    ("docx", "DOCX"),
    ("xlsx", "XLSX"),
    ("jpg", "JPG"),
    ("png", "PNG"),
    ("jpeg", "JPEG"),
]


def document_create(instance):
    employees = instance.employee_id.all()
    for employee in employees:
        document = Document.objects.get_or_create(
            employee_id=employee,
            document_request_id=instance,
            defaults={"title": f"Upload {instance.title}"},
        )
        document[0].title = f"Upload {instance.title}"
        document[0].save()


class DocumentRequest(HorillaModel):
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    employee_id = models.ManyToManyField(Employee, verbose_name=_("Employees"))
    format = models.CharField(choices=FORMATS, max_length=10, verbose_name=_("Format"))
    max_size = models.IntegerField(
        blank=True, null=True, verbose_name=_("Max size (In MB)")
    )
    description = models.TextField(
        blank=True, null=True, max_length=255, verbose_name=_("Description")
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Document Request")
        verbose_name_plural = _("Document Requests")

    def __str__(self):
        return self.title


@receiver(m2m_changed, sender=DocumentRequest.employee_id.through)
def document_request_m2m_changed(sender, instance, action, **kwargs):
    if action == "post_add":
        document_create(instance)

    elif action == "post_remove":
        document_create(instance)


class Document(HorillaModel):
    title = models.CharField(max_length=250)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, verbose_name=_("Employee")
    )
    document_request_id = models.ForeignKey(
        DocumentRequest, on_delete=models.PROTECT, null=True
    )
    document = models.FileField(
        upload_to=upload_path, null=True, verbose_name=_("Document")
    )
    status = models.CharField(
        choices=STATUS, max_length=10, default="requested", verbose_name=_("Status")
    )
    reject_reason = models.TextField(
        blank=True, null=True, max_length=255, verbose_name=_("Reject Reason")
    )
    issue_date = models.DateField(null=True, blank=True, verbose_name=_("Issue Date"))
    expiry_date = models.DateField(null=True, blank=True, verbose_name=_("Expiry Date"))
    notify_before = models.IntegerField(
        default=1, null=True, verbose_name=_("Notify Before")
    )
    is_digital_asset = models.BooleanField(
        default=False, verbose_name=_("Is Digital Asset")
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Document")
        verbose_name_plural = _("Documents")

    def __str__(self) -> str:
        return f"{self.title}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        file = self.document

        if len(self.title) < 3:
            raise ValidationError({"title": _("Title must be at least 3 characters")})

        if file and self.document_request_id:
            format = self.document_request_id.format
            max_size = self.document_request_id.max_size
            if max_size:
                if file.size > max_size * 1024 * 1024:
                    raise ValidationError(
                        {"document": _("File size exceeds the limit")}
                    )

            ext = file.name.split(".")[1].lower()
            if format == "any":
                pass
            elif ext != format:
                raise ValidationError(
                    {"document": _("Please upload {} file only.").format(format)}
                )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_digital_asset:
            if apps.is_installed("asset"):
                from asset.models import Asset, AssetCategory

                asset_category = AssetCategory.objects.get_or_create(
                    asset_category_name="Digital Asset"
                )

                Asset.objects.create(
                    asset_name=self.title,
                    asset_purchase_date=date.today(),
                    asset_category_id=asset_category[0],
                    asset_status="Not-Available",
                    asset_purchase_cost=0,
                    expiry_date=self.expiry_date,
                    notify_before=self.notify_before,
                    asset_tracking_id=f"DIG_ID0{self.pk}",
                )

    def upload_documents_count(self):
        total_requests = Document.objects.filter(
            document_request_id=self.document_request_id
        )
        without_documents = total_requests.filter(document="").count()
        count = total_requests.count() - without_documents
        return count
