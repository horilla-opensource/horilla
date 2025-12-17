"""Django notifications template tags file"""

from django.template import Library
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = Library()


@register.simple_tag(takes_context=True)
def notifications_unread(context):
    user = user_context(context)
    if not user:
        return ""
    return user.notifications.unread().count()


@register.filter
def has_notification(user):
    if user:
        return user.notifications.unread().exists()
    return False


@register.simple_tag
def register_notify_callbacks(
    badge_class="live_notify_badge",
    menu_class="live_notify_list",
    refresh_period=15,
    callbacks="",
    api_name="list",
    fetch=5,
):
    refresh_period = int(refresh_period) * 1000

    if api_name == "list":
        api_url = reverse("notifications:live_unread_notification_list")
    elif api_name == "count":
        api_url = reverse("notifications:live_unread_notification_count")
    else:
        return ""

    script = """
<script>
var notify_badge_class = "{}";
var notify_menu_class = "{}";
var notify_api_url = "{}";
var notify_fetch_count = {};
var notify_unread_url = "{}";
var notify_mark_all_unread_url = "{}";
var notify_refresh_period = {};
""".format(
        badge_class,
        menu_class,
        api_url,
        fetch,
        reverse("notifications:unread"),
        reverse("notifications:mark_all_as_read"),
        refresh_period,
    )

    for callback in callbacks.split(","):
        if callback.strip():
            script += "register_notifier({});\n".format(callback.strip())

    script += "</script>"

    return mark_safe(script)


@register.simple_tag(takes_context=True)
def live_notify_badge(context, *args, badge_class="live_notify_badge", **kwargs):
    user = user_context(context)
    if not user:
        return ""

    return format_html(
        "<span class='{}'>{}</span>",
        badge_class,
        user.notifications.unread().count(),
    )


@register.simple_tag
def live_notify_list(list_class="live_notify_list"):
    return format_html(
        "<ul class='{}'></ul>",
        list_class,
    )


def user_context(context):
    request = context.get("request")
    if not request:
        return None

    user = request.user
    if not user.is_authenticated:
        return None

    return user
