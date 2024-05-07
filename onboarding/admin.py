from django.contrib import admin

from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
    OnboardingStage,
    OnboardingTask,
)

admin.site.register(OnboardingStage)
admin.site.register(OnboardingTask)
admin.site.register(CandidateStage)
admin.site.register(CandidateTask)
admin.site.register(OnboardingPortal)
