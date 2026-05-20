"""
Configuration for horilla_dbtemplate.

Reads from Django settings with HORILLA_DBTEMPLATE_* prefix.
Django 6.x compatible.
"""

from django.conf import settings


def get_setting(name, default=None):
    """Get a setting with HORILLA_DBTEMPLATE_ prefix."""
    full_name = f"HORILLA_DBTEMPLATE_{name}"
    return getattr(settings, full_name, default)


# Cache backend name from CACHES (e.g. "default" or "horilla_dbtemplate")
CACHE_BACKEND = get_setting("CACHE_BACKEND", "default")

# Whether to auto-populate content from filesystem/app loaders when content is empty
AUTO_POPULATE_CONTENT = get_setting("AUTO_POPULATE_CONTENT", False)


def get_cache():
    """Return the cache backend instance, or None if caching is disabled."""
    if not hasattr(settings, "CACHES") or CACHE_BACKEND not in settings.CACHES:
        return None
    try:
        from django.core.cache import caches

        cache = caches[CACHE_BACKEND]
        return cache
    except Exception:
        return None
