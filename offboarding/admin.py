from django.contrib import admin
from offboarding.models import (
    OffboardingStageMultipleFile,
    OffboardingNote,
    OffboardingTask,
    EmployeeTask,
    ResignationLetter,
    OffboardingEmployee,
    OffboardingStage,
)

# Register your models here.

admin.site.register(
    [
        OffboardingStageMultipleFile,
        ResignationLetter,
        OffboardingNote,
        OffboardingTask,
        EmployeeTask,
        OffboardingEmployee,
        OffboardingStage,
    ]
)
