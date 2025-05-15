import os

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Create your models here.


class FaceDetection(models.Model):
    company_id = models.OneToOneField(
        "base.Company", related_name="face_detection", on_delete=models.CASCADE
    )
    start = models.BooleanField(default=False)


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
