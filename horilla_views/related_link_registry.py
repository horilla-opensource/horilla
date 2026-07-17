"""
horilla_views/related_link_registry.py

Framework-level registry mapping models to their detail-view URL builders, used to
auto-linkify related-object values shown in list/detail views (see the `linkify`
template filter in generic_template_filters.py).
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db.models import Model

_registry = {}

# Query param appended to every resolved related-object link so the Detail View
# it opens knows it was reached through related-object navigation (see
# HorillaDetailedView.get_context_data, which reads it to suppress the
# list-driven Previous/Next controls).
RELATED_VIEW_PARAM = "related_view"


def _mark_as_related(url):
    parts = urlsplit(url)
    query = parse_qsl(parts.query)
    query.append((RELATED_VIEW_PARAM, "1"))
    return urlunsplit(parts._replace(query=urlencode(query)))


def register_detail_view(model, get_url=None, url_name=None, permission=None):
    """
    Register how to build (and permission-check) a detail-view link for `model`.

    Provide exactly one of:
      get_url: callable(instance) -> str
      url_name: a URL name reversed with kwargs={"pk": instance.pk}

    `permission` defaults to "<app_label>.view_<model_name>".
    """
    if get_url is None:
        if url_name is None:
            raise ValueError("register_detail_view requires get_url or url_name")
        from django.urls import reverse

        def get_url(instance, _url_name=url_name):
            return reverse(_url_name, kwargs={"pk": instance.pk})

    _registry[model] = {
        "get_url": get_url,
        "permission": permission
        or f"{model._meta.app_label}.view_{model._meta.model_name}",
    }


def resolve_detail_link(instance, user):
    """
    Return a permission-checked detail-view URL for `instance`, or None if
    unavailable (no detail view registered, URL can't be built, or the user lacks
    permission). Never raises.
    """
    if not isinstance(instance, Model):
        return None

    model = type(instance)
    entry = _registry.get(model)
    if entry:
        get_url = entry["get_url"]
        permission = entry["permission"]
    else:
        get_url = getattr(instance, "get_detail_url", None)
        if not callable(get_url):
            return None
        permission = f"{model._meta.app_label}.view_{model._meta.model_name}"

    if user is not None and not user.has_perm(permission):
        return None

    try:
        url = get_url() if entry is None else get_url(instance)
    except Exception:
        return None

    return _mark_as_related(str(url)) if url else None
