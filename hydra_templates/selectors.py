from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from hydra_coordination.models import PersonAssignment
from hydra_coordination.selectors import company_ids_for_user
from hydra_people.selectors import people_for_user
from hydra_templates.models import MessageTemplate


def templates_for_user(*, user, permission="view_messagetemplate"):
    if not user.is_authenticated or not user.has_perm(
        f"hydra_templates.{permission}"
    ):
        return MessageTemplate.objects.none()
    queryset = MessageTemplate.objects.select_related("company")
    if user.is_superuser:
        return queryset
    return queryset.filter(company_id__in=company_ids_for_user(user=user))


def search_templates(*, user, query=""):
    queryset = templates_for_user(user=user)
    query = query.strip()
    if not query:
        return queryset
    return queryset.filter(
        Q(code__icontains=query)
        | Q(name__icontains=query)
        | Q(subject__icontains=query)
    )

def template_for_user(*, user, template_uuid, permission="view_messagetemplate"):
    return get_object_or_404(
        templates_for_user(user=user, permission=permission),
        uuid=template_uuid,
    )


def export_people_for_user(*, user, company=None):
    day = timezone.localdate()
    assignments = (
        PersonAssignment.objects.filter(
            is_active=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .select_related("team__section__location__company", "department")
        .order_by("-is_primary", "-valid_from", "-pk")
    )
    queryset = people_for_user(user=user).order_by("hydra_id")
    if company is not None:
        queryset = queryset.filter(
            coordination_assignments__in=assignments,
            coordination_assignments__team__section__location__company=company,
        ).distinct()
        assignments = assignments.filter(
            team__section__location__company=company
        )
    return queryset.prefetch_related(
        Prefetch(
            "coordination_assignments",
            queryset=assignments,
            to_attr="current_export_assignments",
        )
    )
