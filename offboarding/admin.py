from django.contrib import admin

from offboarding.models import (
    EmployeeTask,
    OffboardingEmployee,
    OffboardingNote,
    OffboardingStage,
    OffboardingStageMultipleFile,
    OffboardingTask,
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
        OffboardingEmployee,
        OffboardingStage,
    ]
)
