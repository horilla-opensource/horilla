from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from hydra_notifications.forms import (
    NotificationFilterForm,
    NotificationPreferenceForm,
)
from hydra_notifications.models import NotificationCategory, NotificationSeverity
from hydra_notifications.selectors import envelope_for_user, visible_envelopes_for_user
from hydra_notifications.services import (
    archive_envelope,
    mark_all_visible_read,
    mark_envelope_read,
    mark_envelope_unread,
    preference_for_user,
    restore_envelope,
    safe_redirect_for_envelope,
    update_preferences,
)


def _service_message(error):
    if hasattr(error, "message_dict"):
        return " ".join(
            str(message)
            for field_messages in error.message_dict.values()
            for message in field_messages
        )
    return " ".join(str(message) for message in error.messages)


@login_required
@never_cache
@require_GET
def notification_center(request):
    filter_form = NotificationFilterForm(request.GET or None)
    filters = {"state": "", "category": "", "severity": ""}
    if filter_form.is_valid():
        filters.update(filter_form.cleaned_data)

    include_archived = filters["state"] == "archived"
    queryset = visible_envelopes_for_user(
        user=request.user,
        include_archived=include_archived,
    )
    if include_archived:
        queryset = queryset.filter(archived_at__isnull=False)
    elif filters["state"] == "unread":
        queryset = queryset.filter(read_at__isnull=True)
    elif filters["state"] == "read":
        queryset = queryset.filter(read_at__isnull=False)
    if filters["category"] in NotificationCategory.values:
        queryset = queryset.filter(category=filters["category"])
    if filters["severity"] in NotificationSeverity.values:
        queryset = queryset.filter(severity=filters["severity"])

    page_obj = Paginator(queryset, 30).get_page(request.GET.get("page"))
    preference = preference_for_user(user=request.user)
    preference_form = NotificationPreferenceForm(preference=preference)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(
        request,
        "hydra_notifications/center.html",
        {
            "filter_form": filter_form,
            "filters": filters,
            "page_obj": page_obj,
            "envelopes": page_obj.object_list,
            "preference_form": preference_form,
            "category_choices": NotificationCategory.choices,
            "severity_choices": NotificationSeverity.choices,
            "filter_query": query_params.urlencode(),
        },
    )


def _state_action(request, envelope_uuid, service, *, include_archived=False):
    envelope = envelope_for_user(
        user=request.user,
        envelope_uuid=envelope_uuid,
        include_archived=include_archived,
    )
    try:
        service(
            actor=request.user,
            envelope_uuid=envelope.uuid,
            expected_version=request.POST.get("version"),
        )
    except ValidationError as error:
        messages.error(request, _service_message(error))
    return redirect("hydra-notification-center")


@login_required
@never_cache
@require_POST
def notification_read(request, envelope_uuid):
    return _state_action(request, envelope_uuid, mark_envelope_read)


@login_required
@never_cache
@require_POST
def notification_unread(request, envelope_uuid):
    return _state_action(request, envelope_uuid, mark_envelope_unread)


@login_required
@never_cache
@require_POST
def notification_archive(request, envelope_uuid):
    return _state_action(request, envelope_uuid, archive_envelope)


@login_required
@never_cache
@require_POST
def notification_restore(request, envelope_uuid):
    return _state_action(
        request,
        envelope_uuid,
        restore_envelope,
        include_archived=True,
    )


@login_required
@never_cache
@require_POST
def notification_open(request, envelope_uuid):
    envelope = envelope_for_user(
        user=request.user,
        envelope_uuid=envelope_uuid,
    )
    try:
        envelope = mark_envelope_read(
            actor=request.user,
            envelope_uuid=envelope.uuid,
            expected_version=request.POST.get("version"),
            opened=True,
        )
    except ValidationError as error:
        messages.error(request, _service_message(error))
        return redirect("hydra-notification-center")
    return redirect(safe_redirect_for_envelope(envelope=envelope))


@login_required
@never_cache
@require_POST
def notification_read_all(request):
    count = mark_all_visible_read(actor=request.user)
    messages.success(
        request,
        _("Marked %(count)s notification(s) as read.") % {"count": count},
    )
    return redirect("hydra-notification-center")


@login_required
@never_cache
@require_POST
def notification_preferences(request):
    preference = preference_for_user(user=request.user)
    form = NotificationPreferenceForm(
        request.POST,
        preference=preference,
    )
    if form.is_valid():
        try:
            update_preferences(
                actor=request.user,
                email_enabled=form.cleaned_data["email_enabled"],
                email_min_severity=form.cleaned_data["email_min_severity"],
                browser_sound_enabled=form.cleaned_data["browser_sound_enabled"],
                expected_version=form.cleaned_data["version"],
            )
        except ValidationError as error:
            messages.error(request, _service_message(error))
        else:
            messages.success(request, _("Notification preferences updated."))
    else:
        messages.error(request, _("Correct the notification preference values."))
    return redirect("hydra-notification-center")
