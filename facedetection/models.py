import os

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Create your models here.


class FaceDetection(models.Model):
    company_id = models.OneToOneField(
        "base.Company",
        related_name="face_detection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    start = models.BooleanField(default=False)

    def clean(self):
        if self.company_id is None:
            qs = FaceDetection.objects.filter(company_id__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    "Only one FaceDetection can have a null company_id."
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensures `clean()` runs
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company_id"],
                name="unique_company_id_when_not_null_facedetection",
                condition=~models.Q(company_id=None),
            )
        ]


class EmployeeFaceDetection(models.Model):
    employee_id = models.OneToOneField(
        "employee.Employee", related_name="face_detection", on_delete=models.CASCADE
    )
    image = models.ImageField()


@receiver(post_delete, sender=EmployeeFaceDetection)
def delete_image_file(sender, instance, **kwargs):
    if instance.image and instance.image.path:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
