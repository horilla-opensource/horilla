from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from hydra_arrivals.models import OnboardingHandoff
from hydra_arrivals.selectors import arrival_plans_for_user
from hydra_legalization.selectors import legalization_cases_for_user
from hydra_notifications.models import (
    HydraNotificationEnvelope,
    NotificationTargetKind,
)
from hydra_people.selectors import people_for_user
from hydra_tasks.selectors import tasks_for_user


def visible_envelopes_for_user(
    *, user, include_archived=False
) -> QuerySet[HydraNotificationEnvelope]:
    if not user.is_authenticated or not user.is_active:
        return HydraNotificationEnvelope._base_manager.none()

    queryset = HydraNotificationEnvelope._base_manager.filter(recipient=user)
    if not include_archived:
        queryset = queryset.filter(archived_at__isnull=True)

    visibility = Q(
        target_kind__in=(
            NotificationTargetKind.GENERAL,
            NotificationTargetKind.ORGANIZATION,
        )
    )
    if user.has_perm("hydra_people.view_person"):
        visibility |= Q(
            target_kind=NotificationTargetKind.PERSON,
            target_uuid__in=people_for_user(user=user).values("uuid"),
        )
    if user.has_perm("hydra_legalization.view_legalizationcase"):
        visibility |= Q(
            target_kind=NotificationTargetKind.LEGALIZATION_CASE,
            target_uuid__in=legalization_cases_for_user(user=user).values("uuid"),
        )
    visible_arrivals = arrival_plans_for_user(user=user)
    visibility |= Q(
        target_kind=NotificationTargetKind.ARRIVAL_PLAN,
        target_uuid__in=visible_arrivals.values("uuid"),
    )
    visibility |= Q(
        target_kind=NotificationTargetKind.ONBOARDING_HANDOFF,
        target_uuid__in=OnboardingHandoff.objects.filter(
            arrival__in=visible_arrivals
        ).values("uuid"),
    )
    visibility |= Q(
        target_kind=NotificationTargetKind.HYDRA_TASK,
        target_uuid__in=tasks_for_user(user=user).values("uuid"),
    )
    return queryset.filter(visibility).select_related(
        "notification",
        "recipient",
        "company",
        "person",
    )


def envelope_for_user(*, user, envelope_uuid, include_archived=False):
    return get_object_or_404(
        visible_envelopes_for_user(
            user=user,
            include_archived=include_archived,
        ),
        uuid=envelope_uuid,
    )


def unread_notification_count(*, user):
    return visible_envelopes_for_user(user=user).filter(read_at__isnull=True).count()


def notification_records_for_tray(*, user, limit=50):
    envelope_ids = visible_envelopes_for_user(user=user).filter(
        read_at__isnull=True
    ).values("notification_id")
    from notifications.models import Notification

    return Notification.objects.filter(pk__in=envelope_ids).order_by(
        "-timestamp", "-pk"
    )[:limit]
