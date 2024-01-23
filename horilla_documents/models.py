from datetime import date
import os
from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext as _
from asset.models import Asset, AssetCategory
from base.horilla_company_manager import HorillaCompanyManager

from employee.models import Employee
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver


STATUS = [
    ('requested', 'Requested'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]
FORMATS = [
    ('any', 'Any'),
    ('pdf', 'PDF'),
    ('txt', 'TXT'),
    ('docx', 'DOCX'),
    ('xlsx', 'XLSX'),
    ('jpg', 'JPG'),
    ('png', 'PNG'),
    ('jpeg', 'JPEG'),
]

def document_create(instance):
    employees = instance.employee_id.all()
    for employee in employees:
        Document.objects.get_or_create(
            title = f"Upload {instance.title}",
            employee_id=employee,
            document_request_id = instance
        )

class DocumentRequest(models.Model):
    title = models.CharField(max_length=100)
    employee_id = models.ManyToManyField(Employee)
    format = models.CharField(choices=FORMATS,max_length=10)
    max_size = models.IntegerField(blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    objects = HorillaCompanyManager()
    is_active = models.BooleanField(default=True)

    def __str__ (self):
        return self.title
    
@receiver(post_save, sender=DocumentRequest)
def doc_request_post_save(sender, instance, **kwargs):
    document_create(instance)

@receiver(m2m_changed, sender=DocumentRequest.employee_id.through)
def your_model_m2m_changed(sender, instance, action, **kwargs):
    if action == 'post_add':
        document_create(instance)

    elif action == 'post_remove':
        document_create(instance)


class Document(models.Model):
    title = models.CharField(max_length=25)
    employee_id = models.ForeignKey(Employee,on_delete=models.PROTECT)
    document_request_id = models.ForeignKey(DocumentRequest,on_delete=models.PROTECT,null=True)
    document = models.FileField(upload_to="employee/documents",null=True)
    status = models.CharField(choices=STATUS, max_length=10,default="requested")
    reject_reason = models.TextField(blank=True,null=True)
    is_digital_asset = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self) -> str:
        return f"{self.title}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        file = self.document

        if file and self.document_request_id:
            format = self.document_request_id.format
            max_size = self.document_request_id.max_size

            if file.size > max_size * 1024 * 1024:
                raise ValidationError("File size exceeds the limit")
            
            ext = file.name.split(".")[1].lower()
            if format == "any":
                pass
            elif ext != format:
                raise ValidationError(f"Please upload {format} file only.")
            
    def save(self,*args, **kwargs):
        if len(self.title)<3:
            raise ValidationError(_("Title must be at least 3 characters"))
        if self.is_digital_asset:
            asset_category = AssetCategory.objects.get_or_create(asset_category_name ="Digital Asset")
            
            Asset.objects.create(
                asset_name = self.title,
                asset_purchase_date = date.today(),
                asset_category_id = asset_category[0],
                asset_status = "Not-Available",
                asset_purchase_cost=0,
            )
            
        super().save(*args, **kwargs)

