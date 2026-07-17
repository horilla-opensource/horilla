from django.contrib import admin

from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationAuthorityEvent,
    LegalizationAutomationEvent,
    LegalizationCase,
    LegalizationCaseDelegation,
    LegalizationCaseDocument,
    LegalizationConfigurationEvent,
    LegalizationProcedureRequirement,
    LegalizationProcedureStatus,
    LegalizationProcedureType,
    LegalizationRenewalLink,
    LegalizationStatusHistory,
    LegalizationWorkEvent,
)
from hydra_legalization.selectors import (
    legalization_authorities_for_user,
    legalization_cases_for_user,
    legalization_procedures_for_user,
    legalization_requirements_for_user,
    renewal_links_for_user,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SuperuserReadOnlyAdmin(ReadOnlyAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if request.user.is_superuser else queryset.none()


class ScopedCaseAdmin(ReadOnlyAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        visible = legalization_cases_for_user(user=request.user).values_list(
            "pk", flat=True
        )
        return queryset.filter(pk__in=visible)

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return obj is None or legalization_cases_for_user(user=request.user).filter(
            pk=obj.pk
        ).exists()


class ScopedRelatedAdmin(ReadOnlyAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        visible = legalization_cases_for_user(user=request.user).values_list(
            "pk", flat=True
        )
        return queryset.filter(case_id__in=visible)

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return obj is None or legalization_cases_for_user(user=request.user).filter(
            pk=obj.case_id
        ).exists()


class ScopedRenewalAdmin(ReadOnlyAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        visible = renewal_links_for_user(user=request.user).values_list("pk", flat=True)
        return queryset.filter(pk__in=visible)

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return obj is None or renewal_links_for_user(user=request.user).filter(
            pk=obj.pk
        ).exists()


@admin.register(LegalizationCase)
class LegalizationCaseAdmin(ScopedCaseAdmin):
    list_display = (
        "uuid",
        "person",
        "company",
        "procedure_type",
        "case_type",
        "status",
        "responsible",
        "deadline",
        "valid_until",
    )
    list_filter = ("company", "procedure_type", "case_type", "status", "deadline", "valid_until")
    search_fields = ("uuid", "person__hydra_id", "person__passport_name", "reference_number")


@admin.register(LegalizationCaseDelegation)
class LegalizationCaseDelegationAdmin(ScopedRelatedAdmin):
    list_display = (
        "case",
        "principal",
        "deputy",
        "valid_from",
        "valid_until",
        "is_active",
        "revoked_at",
    )
    list_filter = ("is_active", "valid_from", "valid_until", "revoked_at")
    search_fields = (
        "uuid",
        "case__uuid",
        "case__person__hydra_id",
        "principal__username",
        "deputy__username",
    )


@admin.register(LegalizationWorkEvent)
class LegalizationWorkEventAdmin(ScopedRelatedAdmin):
    list_display = (
        "occurred_at",
        "case",
        "action",
        "from_user",
        "to_user",
        "actor",
        "notification_status",
    )
    list_filter = ("action", "source", "notification_status", "occurred_at")
    search_fields = (
        "uuid",
        "case__uuid",
        "case__person__hydra_id",
        "from_user__username",
        "to_user__username",
    )


@admin.register(LegalizationStatusHistory)
class LegalizationStatusHistoryAdmin(ScopedRelatedAdmin):
    list_display = (
        "occurred_at",
        "case",
        "from_status",
        "to_status",
        "source",
        "actor",
        "reason",
    )
    list_filter = ("to_status", "source", "occurred_at")


@admin.register(LegalizationAutomationEvent)
class LegalizationAutomationEventAdmin(ScopedRelatedAdmin):
    list_display = (
        "occurred_at",
        "case",
        "event_type",
        "due_date",
        "threshold_days",
        "recipient",
        "notification_status",
        "notification_attempts",
    )
    list_filter = ("event_type", "notification_status", "occurred_at")
    search_fields = ("uuid", "case__uuid", "recipient__username")


@admin.register(LegalizationCaseDocument)
class LegalizationCaseDocumentAdmin(ScopedRelatedAdmin):
    list_display = ("case", "document", "role", "created_at", "created_by")
    list_filter = ("role", "created_at")


@admin.register(LegalizationAuthorityEvent)
class LegalizationAuthorityEventAdmin(ScopedRelatedAdmin):
    list_display = (
        "recorded_at",
        "case",
        "event_type",
        "occurred_on",
        "authority",
        "channel",
        "actor",
    )
    list_filter = ("event_type", "channel", "occurred_on", "recorded_at")
    search_fields = ("uuid", "case__uuid", "case__person__hydra_id", "reference_number")


@admin.register(LegalizationRenewalLink)
class LegalizationRenewalLinkAdmin(ScopedRenewalAdmin):
    list_display = (
        "created_at",
        "predecessor",
        "successor",
        "source",
        "actor",
    )
    list_filter = ("source", "created_at")
    search_fields = (
        "uuid",
        "predecessor__uuid",
        "successor__uuid",
        "predecessor__person__hydra_id",
    )


@admin.register(LegalizationProcedureType)
class LegalizationProcedureTypeAdmin(ReadOnlyAdmin):
    list_display = ("name", "code", "company", "case_type", "is_active")
    list_filter = ("company", "case_type", "is_active")
    search_fields = ("uuid", "code", "name")

    def get_queryset(self, request):
        visible = legalization_procedures_for_user(
            user=request.user, include_inactive=True
        ).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=visible)


@admin.register(LegalizationAuthority)
class LegalizationAuthorityAdmin(ReadOnlyAdmin):
    list_display = ("name", "code", "company", "jurisdiction", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("uuid", "code", "name", "jurisdiction")

    def get_queryset(self, request):
        visible = legalization_authorities_for_user(
            user=request.user, include_inactive=True
        ).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=visible)


@admin.register(LegalizationProcedureRequirement)
class LegalizationProcedureRequirementAdmin(ReadOnlyAdmin):
    list_display = (
        "name",
        "procedure",
        "document_type",
        "required_before_status",
        "is_active",
    )
    list_filter = ("required_before_status", "is_active")
    search_fields = ("uuid", "code", "name", "procedure__name")

    def get_queryset(self, request):
        visible = legalization_requirements_for_user(
            user=request.user, include_inactive=True
        ).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=visible)


@admin.register(LegalizationProcedureStatus)
class LegalizationProcedureStatusAdmin(SuperuserReadOnlyAdmin):
    list_display = ("procedure", "status", "label", "sort_order", "is_active")
    list_filter = ("status", "is_active")


@admin.register(LegalizationConfigurationEvent)
class LegalizationConfigurationEventAdmin(SuperuserReadOnlyAdmin):
    list_display = (
        "occurred_at",
        "entity_type",
        "entity_uuid",
        "action",
        "reason",
        "actor",
    )
    list_filter = ("entity_type", "action", "occurred_at")
    search_fields = ("uuid", "entity_uuid", "actor__username")
