from dataclasses import dataclass

from hydra_notifications.models import (
    NotificationCategory,
    NotificationKind,
    NotificationSeverity,
)


@dataclass(frozen=True)
class NotificationPolicy:
    message: str
    category: str
    severity: str
    icon: str


POLICIES = {
    NotificationKind.ORGANIZATION_SCOPE_END: NotificationPolicy(
        "Your Hydra organization access is scheduled to end.",
        NotificationCategory.ORGANIZATION,
        NotificationSeverity.WARNING,
        "shield-outline",
    ),
    NotificationKind.ORGANIZATION_SCOPE_REVOKED: NotificationPolicy(
        "Your Hydra organization access was revoked.",
        NotificationCategory.ORGANIZATION,
        NotificationSeverity.ERROR,
        "shield-outline",
    ),
    NotificationKind.ORGANIZATION_ASSIGNMENT_END: NotificationPolicy(
        "Your Hydra organization assignment is scheduled to end.",
        NotificationCategory.ORGANIZATION,
        NotificationSeverity.WARNING,
        "shield-outline",
    ),
    NotificationKind.ORGANIZATION_ASSIGNMENT_ENDED: NotificationPolicy(
        "Your Hydra organization assignment ended.",
        NotificationCategory.ORGANIZATION,
        NotificationSeverity.ERROR,
        "shield-outline",
    ),
    NotificationKind.ARRIVAL_UPCOMING: NotificationPolicy(
        "A planned arrival is approaching.",
        NotificationCategory.ARRIVALS,
        NotificationSeverity.WARNING,
        "time-outline",
    ),
    NotificationKind.ARRIVAL_OVERDUE: NotificationPolicy(
        "A planned arrival is overdue and needs review.",
        NotificationCategory.ARRIVALS,
        NotificationSeverity.ERROR,
        "alert-circle-outline",
    ),
    NotificationKind.LEGALIZATION_DEADLINE: NotificationPolicy(
        "A legalization workflow deadline is approaching.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "warning-outline",
    ),
    NotificationKind.LEGALIZATION_OVERDUE: NotificationPolicy(
        "A legalization workflow deadline is overdue.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.ERROR,
        "warning-outline",
    ),
    NotificationKind.LEGALIZATION_VALIDITY: NotificationPolicy(
        "An approved legalization validity period is approaching its end.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "calendar-outline",
    ),
    NotificationKind.LEGALIZATION_EXPIRED: NotificationPolicy(
        "An approved legalization case expired automatically.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.ERROR,
        "warning-outline",
    ),
    NotificationKind.LEGALIZATION_ASSIGNED: NotificationPolicy(
        "Responsibility for a legalization case was assigned to you.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "people-outline",
    ),
    NotificationKind.LEGALIZATION_TRANSFERRED: NotificationPolicy(
        "Responsibility for a legalization case was transferred to you.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "people-outline",
    ),
    NotificationKind.LEGALIZATION_DEPUTY: NotificationPolicy(
        "You were appointed as deputy for a legalization case.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "people-outline",
    ),
    NotificationKind.LEGALIZATION_DEPUTY_REVOKED: NotificationPolicy(
        "Your deputy appointment for a legalization case was revoked.",
        NotificationCategory.LEGALIZATION,
        NotificationSeverity.WARNING,
        "people-outline",
    ),
    NotificationKind.TASK_ASSIGNED: NotificationPolicy(
        "A Hydra task was assigned to you.",
        NotificationCategory.TASKS,
        NotificationSeverity.WARNING,
        "checkmark-done-outline",
    ),
    NotificationKind.TASK_UPDATED: NotificationPolicy(
        "A Hydra task assigned to you was updated.",
        NotificationCategory.TASKS,
        NotificationSeverity.INFO,
        "checkmark-done-outline",
    ),
    NotificationKind.TASK_REASSIGNED: NotificationPolicy(
        "A Hydra task was reassigned to you.",
        NotificationCategory.TASKS,
        NotificationSeverity.WARNING,
        "checkmark-done-outline",
    ),
    NotificationKind.TASK_STATUS_CHANGED: NotificationPolicy(
        "A Hydra task status changed.",
        NotificationCategory.TASKS,
        NotificationSeverity.INFO,
        "checkmark-done-outline",
    ),
    NotificationKind.TASK_COMPLETED: NotificationPolicy(
        "A Hydra task was completed.",
        NotificationCategory.TASKS,
        NotificationSeverity.SUCCESS,
        "checkmark-circle-outline",
    ),
    NotificationKind.TASK_CANCELLED: NotificationPolicy(
        "A Hydra task was cancelled.",
        NotificationCategory.TASKS,
        NotificationSeverity.WARNING,
        "close-circle-outline",
    ),
    NotificationKind.TASK_REOPENED: NotificationPolicy(
        "A Hydra task was reopened.",
        NotificationCategory.TASKS,
        NotificationSeverity.WARNING,
        "refresh-outline",
    ),
    NotificationKind.ONBOARDING_READY: NotificationPolicy(
        "A confirmed arrival is ready for onboarding.",
        NotificationCategory.ONBOARDING,
        NotificationSeverity.INFO,
        "people-outline",
    ),
    NotificationKind.ONBOARDING_TASK_CHANGED: NotificationPolicy(
        "An onboarding task status changed.",
        NotificationCategory.ONBOARDING,
        NotificationSeverity.INFO,
        "people-outline",
    ),
}


SEVERITY_RANK = {
    NotificationSeverity.INFO: 10,
    NotificationSeverity.SUCCESS: 20,
    NotificationSeverity.WARNING: 30,
    NotificationSeverity.ERROR: 40,
}


def policy_for(kind):
    try:
        return POLICIES[kind]
    except KeyError as error:
        raise ValueError("A managed notification requires a reviewed kind.") from error


def severity_meets_threshold(*, severity, threshold):
    return SEVERITY_RANK[severity] >= SEVERITY_RANK[threshold]
