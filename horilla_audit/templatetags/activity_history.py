"""
Template tags for the shared activity-history feed UI.
"""

import uuid

from django import template
from django.utils.translation import gettext as _

from horilla_audit.activity_feed import build_activity_history_feed

register = template.Library()


@register.inclusion_tag("generic/activity_history_feed.html", takes_context=True)
def activity_history_feed(
    context,
    tracking=None,
    log_entries=None,
    show_header=True,
    show_search=True,
    title=None,
    subtitle=None,
    empty_message=None,
    compact=False,
    feed_id=None,
    has_perm_to_revert=False,
    object=None,
    model=None,
):
    """
    Render the shared activity-history timeline.

    Usage:
        {% load activity_history %}
        {% activity_history_feed tracking=candidate.tracking %}
    """

    def _as_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}

    feed = build_activity_history_feed(tracking=tracking, log_entries=log_entries)
    return {
        **feed,
        "show_header": _as_bool(show_header, True),
        "show_search": _as_bool(show_search, True),
        "title": title or _("Activity history"),
        "subtitle": (
            subtitle if subtitle is not None else _("All changes made to this record")
        ),
        "empty_message": empty_message or _("No changes recorded yet"),
        "compact": _as_bool(compact, False),
        "feed_id": feed_id or f"activityHistoryFeed-{uuid.uuid4().hex[:8]}",
        "has_perm_to_revert": _as_bool(
            has_perm_to_revert, bool(context.get("has_perm_to_revert"))
        ),
        "object": object if object is not None else context.get("object"),
        "model": model if model is not None else context.get("model"),
        "request": context.get("request"),
    }
