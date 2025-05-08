from django.db import models

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
