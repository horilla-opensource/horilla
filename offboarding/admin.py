from django.contrib import admin
from offboarding.models import (
    OffboardingStageMultipleFile,
    OffboardingNote,
    OffboardingTask,
    EmployeeTask,
    ResignationLetter,
)

# Register your models here.

admin.site.register(
    [
        OffboardingStageMultipleFile,
        ResignationLetter,
        OffboardingNote,
        OffboardingTask,
        EmployeeTask,
    ]
)
