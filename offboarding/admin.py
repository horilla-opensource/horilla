from django.contrib import admin
from offboarding.models import (
    OffboardingStageMultipleFile,
    OffboardingNote,
    OffboardingTask,
    EmployeeTask,
)

# Register your models here.

admin.site.register(
    [OffboardingStageMultipleFile, OffboardingNote, OffboardingTask, EmployeeTask]
)
