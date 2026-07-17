# -*- coding: utf-8 -*-
"""Django Notifications example views"""
from distutils.version import (  # pylint: disable=no-name-in-module,import-error
    StrictVersion,
)

from django import get_version
from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.http import HttpResponse  # noqa
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from swapper import load_model

from notifications import settings
from notifications.settings import get_config
from notifications.utils import id2slug, slug2id

Notification = load_model("notifications", "Notification")


def _visible_notification_queryset(user, *, include_archived=False):
    from hydra_notifications.selectors import visible_envelopes_for_user

    notification_ids = visible_envelopes_for_user(
        user=user,
        include_archived=include_archived,
    ).values("notification_id")
    return Notification.objects.filter(pk__in=notification_ids)

if StrictVersion(get_version()) >= StrictVersion("1.7.0"):
    from django.http import JsonResponse  # noqa
else:
    # Django 1.6 doesn't have a proper JsonResponse
    import json

    def date_handler(obj):
        return obj.isoformat() if hasattr(obj, "isoformat") else obj

    def JsonResponse(data):  # noqa
        return HttpResponse(
            json.dumps(data, default=date_handler), content_type="application/json"
        )


class NotificationViewList(ListView):
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = settings.get_config()["PAGINATE_BY"]

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(NotificationViewList, self).dispatch(request, *args, **kwargs)


class AllNotificationsList(NotificationViewList):
    """
    Index page for authenticated user
    """

    def get_queryset(self):
        return _visible_notification_queryset(self.request.user)


class UnreadNotificationsList(NotificationViewList):

    def get_queryset(self):
        return _visible_notification_queryset(self.request.user).filter(unread=True)


@login_required
@require_POST
def mark_all_as_read(request):
    from hydra_notifications.services import mark_all_visible_read

    mark_all_visible_read(actor=request.user)

    _next = request.GET.get("next")

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))
    return redirect("notifications:unread")


@login_required
@require_POST
def mark_as_read(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id
    )
    from hydra_notifications.services import mark_envelope_read, wrap_legacy_notification

    envelope = wrap_legacy_notification(notification=notification)
    mark_envelope_read(actor=request.user, envelope_uuid=envelope.uuid)

    _next = request.GET.get("next")

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect("notifications:unread")


@login_required
@require_POST
def mark_as_unread(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id
    )
    from hydra_notifications.services import mark_envelope_unread, wrap_legacy_notification

    envelope = wrap_legacy_notification(notification=notification)
    mark_envelope_unread(actor=request.user, envelope_uuid=envelope.uuid)

    _next = request.GET.get("next")

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect("notifications:unread")


@login_required
@require_POST
def delete(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id
    )

    from hydra_notifications.services import archive_envelope, wrap_legacy_notification

    envelope = wrap_legacy_notification(notification=notification)
    archive_envelope(actor=request.user, envelope_uuid=envelope.uuid)

    _next = request.GET.get("next")

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect("notifications:all")


@never_cache
def live_unread_notification_count(request):
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {"unread_count": 0}
    else:
        from hydra_notifications.selectors import unread_notification_count

        data = {
            "unread_count": unread_notification_count(user=request.user),
        }
    return JsonResponse(data)


@never_cache
def live_unread_notification_list(request):
    """Return a json with a unread notification list"""
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {"unread_count": 0, "unread_list": []}
        return JsonResponse(data)

    default_num_to_fetch = get_config()["NUM_TO_FETCH"]
    try:
        # If they don't specify, make it 5.
        num_to_fetch = request.GET.get("max", default_num_to_fetch)
        num_to_fetch = int(num_to_fetch)
        if not (1 <= num_to_fetch <= 100):
            num_to_fetch = default_num_to_fetch
    except ValueError:  # If casting to an int fails.
        num_to_fetch = default_num_to_fetch

    unread_list = []

    notifications = _visible_notification_queryset(request.user).filter(unread=True)
    for notification in notifications[0:num_to_fetch]:
        struct = model_to_dict(notification)
        struct["slug"] = id2slug(notification.id)
        if notification.actor:
            struct["actor"] = str(notification.actor)
        if notification.target:
            struct["target"] = str(notification.target)
        if notification.action_object:
            struct["action_object"] = str(notification.action_object)
        if notification.data:
            struct["data"] = notification.data
        unread_list.append(struct)
        # GET endpoints are read-only; state changes require CSRF-protected POST.
    data = {
        "unread_count": notifications.count(),
        "unread_list": unread_list,
    }
    return JsonResponse(data)


@never_cache
def live_all_notification_list(request):
    """Return a json with a unread notification list"""
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {"all_count": 0, "all_list": []}
        return JsonResponse(data)

    default_num_to_fetch = get_config()["NUM_TO_FETCH"]
    try:
        # If they don't specify, make it 5.
        num_to_fetch = request.GET.get("max", default_num_to_fetch)
        num_to_fetch = int(num_to_fetch)
        if not (1 <= num_to_fetch <= 100):
            num_to_fetch = default_num_to_fetch
    except ValueError:  # If casting to an int fails.
        num_to_fetch = default_num_to_fetch

    all_list = []

    notifications = _visible_notification_queryset(request.user)
    for notification in notifications[0:num_to_fetch]:
        struct = model_to_dict(notification)
        struct["slug"] = id2slug(notification.id)
        if notification.actor:
            struct["actor"] = str(notification.actor)
        if notification.target:
            struct["target"] = str(notification.target)
        if notification.action_object:
            struct["action_object"] = str(notification.action_object)
        if notification.data:
            struct["data"] = notification.data
        all_list.append(struct)
    data = {"all_count": notifications.count(), "all_list": all_list}
    return JsonResponse(data)


def live_all_notification_count(request):
    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {"all_count": 0}
    else:
        data = {
            "all_count": _visible_notification_queryset(request.user).count(),
        }
    return JsonResponse(data)


@login_required
@require_POST
def notification_sound(request):
    from hydra_notifications.services import toggle_browser_sound

    toggle_browser_sound(actor=request.user)

    return HttpResponse("")
