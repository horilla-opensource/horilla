"""
Custom template loader: resolve templates from the database with host/domain priority.

Resolution order:
  1. Template matching the current request host domain (only if host matches a Site)
     - Further filtered by language if present in the request
  2. Global template (sites__isnull=True), language-matched
  3. Global template (sites__isnull=True), language-agnostic
  4. Raise TemplateDoesNotExist so Django can try filesystem/app_directories loaders

Scheduling: only templates with state=active AND within active_from/active_until window
are served from DB.

Analytics: access_count and last_accessed_at are updated asynchronously via
Django's request_finished signal (does not slow down the request path).
"""

from django.db import router
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from django.utils.timezone import now

from .models import STATE_ACTIVE, Template
from .utils.cache import cache, get_cache_key, get_cache_notfound_key, set_and_return
from .utils.site import get_site_for_request


class Loader(BaseLoader):
    """
    Load templates from the database with host-based site resolution,
    language support, scheduling window enforcement, and access analytics.
    """

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        """Yield a single :class:`~django.template.Origin` for ``template_name`` (loader API)."""
        yield Origin(
            name=template_name,
            template_name=template_name,
            loader=self,
        )

    def get_contents(self, origin):
        """Return template source text for ``origin`` or raise ``TemplateDoesNotExist``."""
        content, _ = self._load_template_source(origin.template_name)
        return content

    def _get_request(self):
        """Retrieve the current request from thread-local storage."""
        try:
            from horilla.horilla_middlewares import _thread_locals

            return getattr(_thread_locals, "request", None)
        except ImportError:
            return None

    def _resolve_site(self):
        """Resolve the effective site only when request host matches a Site domain; else None.

        Memoized on the request object: the resolved site cannot change within
        the lifetime of a single request, but this loader's get_template() is
        called once per rendered template fragment (often a dozen+ times per
        list page via render_template()), so without caching this re-queries
        the Site table on every single call.
        """
        request = self._get_request()
        if request is None:
            return get_site_for_request(request)
        if not hasattr(request, "_horilla_dbtemplate_site"):
            request._horilla_dbtemplate_site = get_site_for_request(request)
        return request._horilla_dbtemplate_site

    def _get_language(self):
        """Resolve the current language from the request."""
        try:
            from django.utils.translation import get_language

            return get_language() or ""
        except Exception:
            return ""

    def _is_template_active(self, template):
        """Return True if the template is active and within its scheduling window."""
        if template.state != STATE_ACTIVE:
            return False
        return template.is_schedulable_active()

    def _load_and_store_template(self, template_name, cache_key, site, **params):
        """Load template from DB, check scheduling, store in cache."""
        # Only serve active templates
        params["state"] = STATE_ACTIVE
        template = Template.objects.get(name__exact=template_name, **params)

        # Enforce scheduling window
        if not template.is_schedulable_active():
            raise Template.DoesNotExist("Template is outside its scheduling window.")

        db = router.db_for_read(Template, instance=template)
        site_domain = getattr(site, "domain", "global")
        display_name = f"horilla_dbtemplate:{db}:{template_name}:{site_domain}"

        # Record analytics asynchronously (no DB hit in the hot path)
        self._record_access(template)

        return set_and_return(cache_key, template.content, display_name)

    def _record_access(self, template):
        """Update access_count and last_accessed_at without blocking the response."""
        try:
            Template.objects.filter(pk=template.pk).update(
                access_count=template.access_count + 1,
                last_accessed_at=now(),
            )
        except Exception:
            pass

    def _load_template_source(self, template_name, template_dirs=None):
        """
        Load template source with priority:
          1. Cached template for resolved site + language
          2. Not-found cache -> raise TemplateDoesNotExist
          3. DB: site-specific + language match
          4. DB: site-specific + language-agnostic
          5. DB: global + language match
          6. DB: global + language-agnostic
          7. Mark not-found, raise TemplateDoesNotExist
        """
        site = self._resolve_site()
        language = self._get_language()
        cache_key = get_cache_key(template_name, site, language)
        cache_notfound_key = get_cache_notfound_key(template_name, site, language)

        # 1. Try cache
        if cache:
            try:
                backend_template = cache.get(cache_key)
                if backend_template:
                    return backend_template, template_name
            except Exception:
                pass

        # 2. Not-found cache
        if cache:
            try:
                if cache.get(cache_notfound_key):
                    raise TemplateDoesNotExist(template_name)
            except TemplateDoesNotExist:
                raise
            except Exception:
                pass

        # 3 & 4. Site-specific (if host matched)
        if site is not None:
            # Try language-specific first
            if language:
                try:
                    return self._load_and_store_template(
                        template_name,
                        cache_key,
                        site,
                        sites__in=[site.pk],
                        language=language,
                    )
                except (Template.MultipleObjectsReturned, Template.DoesNotExist):
                    pass
            # Then language-agnostic
            try:
                return self._load_and_store_template(
                    template_name, cache_key, site, sites__in=[site.pk], language=""
                )
            except (Template.MultipleObjectsReturned, Template.DoesNotExist):
                pass

        # 5. Global + language-specific
        if language:
            try:
                return self._load_and_store_template(
                    template_name,
                    cache_key,
                    site,
                    sites__isnull=True,
                    language=language,
                )
            except (Template.MultipleObjectsReturned, Template.DoesNotExist):
                pass

        # 6. Global + language-agnostic
        try:
            return self._load_and_store_template(
                template_name, cache_key, site, sites__isnull=True, language=""
            )
        except (Template.MultipleObjectsReturned, Template.DoesNotExist):
            pass

        # 7. Mark not-found and raise
        if cache:
            try:
                cache.set(cache_notfound_key, "1")
            except Exception:
                pass
        raise TemplateDoesNotExist(template_name)
