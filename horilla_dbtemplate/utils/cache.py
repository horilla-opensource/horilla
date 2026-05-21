"""
Cache utilities for horilla_dbtemplate.

Cache keys include the resolved site and language so that the same template name
can resolve to different content per site/language. Avoids DB hits when cached.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import signals
from django.template.defaultfilters import slugify

from ..conf import get_cache


def _iter_request_language_codes():
    """
    Languages the DB loader may use in ``get_cache_key`` (via ``get_language()``).

    Cache invalidation must cover every variant; template rows often have
    ``language=""`` while the loader still caches under the active locale (e.g. en).
    """
    yield ""
    lc = getattr(settings, "LANGUAGE_CODE", "") or ""
    if lc.strip():
        yield lc
    for code, _ in getattr(settings, "LANGUAGES", ()) or ():
        if code:
            yield code


def _iter_warm_languages_for_instance(instance):
    """Languages to populate when warming cache for this template row."""
    if instance.language:
        yield instance.language
        yield ""
        return
    yield from _iter_request_language_codes()


cache = get_cache()

if cache is not None:
    try:
        signals.request_finished.connect(cache.close)
    except Exception:
        pass


def get_cache_key(template_name, site=None, language=""):
    """
    Return cache key for a template, optional site, and optional language.

    - site=None -> key for global template (sites__isnull=True)
    - site=Site instance -> key for that site
    - language="" -> language-agnostic key
    """
    site_id = "global" if site is None else getattr(site, "pk", "global")
    lang = slugify(language) if language else "all"
    return f"horilla_dbtemplate::{slugify(template_name)}::{site_id}::{lang}"


def get_cache_notfound_key(template_name, site=None, language=""):
    """Key used to remember that a template was not found (avoid repeated DB misses)."""
    return get_cache_key(template_name, site, language) + "::notfound"


def set_and_return(cache_key, content, display_name):
    """Store content in cache and return (content, display_name) for the loader."""
    if cache:
        try:
            cache.set(cache_key, content)
        except Exception:
            pass
    return (content, display_name)


def remove_notfound_key(template_name, site=None, language=""):
    """Remove the notfound marker for a template/site/language."""
    if cache:
        try:
            cache.delete(get_cache_notfound_key(template_name, site, language))
        except Exception:
            pass


def remove_cached_template(instance, **kwargs):
    """
    Drop cached template source for this template name.

    Clears the global key and every Site key (not only sites currently on the
    instance). That way, when ManyToMany is updated after ``post_save`` (admin /
    ModelForm order), or when a template becomes global, stale per-host cache
    entries are still removed.
    """
    if not cache:
        return

    try:
        all_sites = list(Site.objects.all())
    except Exception:
        all_sites = []

    for language in _iter_request_language_codes():
        try:
            cache.delete(get_cache_key(instance.name, None, language))
        except Exception:
            pass
        remove_notfound_key(instance.name, None, language)

        for site in all_sites:
            try:
                cache.delete(get_cache_key(instance.name, site, language))
            except Exception:
                pass
            remove_notfound_key(instance.name, site, language)


def warm_template_cache(instance):
    """Write ``instance`` into cache for its current sites/languages (no deletes)."""
    if not cache or not instance.content:
        return

    for language in _iter_warm_languages_for_instance(instance):
        if instance.sites.exists():
            for site in instance.sites.all():
                try:
                    cache.set(
                        get_cache_key(instance.name, site, language), instance.content
                    )
                except Exception:
                    pass
        else:
            try:
                cache.set(
                    get_cache_key(instance.name, None, language), instance.content
                )
            except Exception:
                pass


def add_template_to_cache(instance, **kwargs):
    """
    On template save (or admin actions): clear all keys for this name, then warm.
    """
    remove_cached_template(instance, **kwargs)
    warm_template_cache(instance)
