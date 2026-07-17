from django.contrib import admin

from hydra_people.models import (
    CandidateStageTransition,
    EmployeeConversion,
    Person,
    PersonApplication,
    PersonDuplicateSuggestion,
    PersonMergeEvent,
    PersonMergeReference,
    RecruitmentStageTransitionRule,
)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "hydra_id",
        "passport_name",
        "date_of_birth",
        "citizenship",
        "lifecycle_state",
        "employee",
        "merged_into",
        "is_active",
    )
    list_filter = ("lifecycle_state", "citizenship", "preferred_language", "is_active")
    search_fields = ("hydra_id", "passport_name", "first_name", "last_name", "email")
    readonly_fields = (
        "uuid",
        "hydra_id",
        "employee",
        "identity_fingerprint",
        "passport_dob_fingerprint",
        "email_fingerprint",
        "phone_fingerprint",
        "messenger_fingerprint",
        "merged_into",
        "merged_at",
        "merged_by",
        "created_at",
        "created_by",
        "modified_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PersonDuplicateSuggestion)
class PersonDuplicateSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "person_low",
        "person_high",
        "score",
        "state",
        "last_evaluated_at",
        "resolved_by",
    )
    list_filter = ("state", "score")
    search_fields = (
        "person_low__hydra_id",
        "person_high__hydra_id",
        "person_low__passport_name",
        "person_high__passport_name",
    )
    readonly_fields = tuple(
        field.name for field in PersonDuplicateSuggestion._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PersonMergeEvent)
class PersonMergeEventAdmin(admin.ModelAdmin):
    list_display = ("survivor", "duplicate", "actor", "occurred_at")
    search_fields = (
        "survivor__hydra_id",
        "duplicate__hydra_id",
        "survivor__passport_name",
        "duplicate__passport_name",
    )
    readonly_fields = tuple(field.name for field in PersonMergeEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PersonMergeReference)
class PersonMergeReferenceAdmin(admin.ModelAdmin):
    list_display = ("event", "relation_kind", "object_id", "occurred_at")
    list_filter = ("relation_kind",)
    readonly_fields = tuple(field.name for field in PersonMergeReference._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PersonApplication)
class PersonApplicationAdmin(admin.ModelAdmin):
    list_display = ("person", "candidate", "created_at", "created_by")
    search_fields = (
        "person__hydra_id",
        "person__passport_name",
        "candidate__name",
        "candidate__email",
    )
    readonly_fields = ("created_at", "created_by", "modified_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmployeeConversion)
class EmployeeConversionAdmin(admin.ModelAdmin):
    list_display = ("person", "employee", "candidate", "source", "actor", "occurred_at")
    search_fields = (
        "person__hydra_id",
        "person__passport_name",
        "employee__email",
        "candidate__email",
    )
    readonly_fields = (
        "person",
        "employee",
        "candidate",
        "source",
        "actor",
        "source_snapshot",
        "field_decisions",
        "occurred_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecruitmentStageTransitionRule)
class RecruitmentStageTransitionRuleAdmin(admin.ModelAdmin):
    list_display = (
        "recruitment",
        "from_stage",
        "to_stage",
        "requires_reason",
        "requires_schedule_date",
        "requires_joining_date",
        "allow_override",
        "is_active",
    )
    list_filter = (
        "recruitment",
        "requires_reason",
        "requires_schedule_date",
        "requires_joining_date",
        "allow_override",
        "is_active",
    )
    list_editable = (
        "requires_reason",
        "requires_schedule_date",
        "requires_joining_date",
        "allow_override",
        "is_active",
    )
    readonly_fields = ("created_at", "created_by", "modified_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CandidateStageTransition)
class CandidateStageTransitionAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "from_stage",
        "to_stage",
        "source",
        "override",
        "actor",
        "occurred_at",
    )
    list_filter = ("source", "override", "to_stage__stage_type")
    search_fields = ("candidate__name", "candidate__email", "reason")
    readonly_fields = (
        "candidate",
        "from_stage",
        "to_stage",
        "rule",
        "actor",
        "source",
        "reason",
        "override",
        "requirements_snapshot",
        "occurred_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
