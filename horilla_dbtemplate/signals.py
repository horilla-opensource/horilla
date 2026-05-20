"""Invalidate and warm DB template loader cache when ``Template`` rows or M2M sites change."""

from django.db import transaction
from django.db.models import signals
from django.db.models.signals import m2m_changed

from .models import Template
from .utils.cache import remove_cached_template, warm_template_cache


def _schedule_warm_template_cache(pk):
    """Warm cache after DB state (including M2M) is committed."""

    def _warm():
        try:
            fresh = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return
        warm_template_cache(fresh)

    transaction.on_commit(_warm)


def invalidate_template_cache_on_save(sender, instance, **kwargs):
    """
    ModelForm / admin save order is ``save()`` then ``_save_m2m()``.

    ``post_save`` runs while ``sites`` still reflects the *previous* assignment,
    so we clear cache immediately, then repopulate only ``on_commit`` when M2M
    matches the database.
    """
    remove_cached_template(instance, **kwargs)
    if instance.pk:
        _schedule_warm_template_cache(instance.pk)


def invalidate_template_cache_on_sites_changed(sender, instance, action, **kwargs):
    """Sites edited without a full ``Template.save()`` (or after M2M flush)."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    remove_cached_template(instance, **kwargs)
    if instance.pk:
        _schedule_warm_template_cache(instance.pk)


signals.post_save.connect(invalidate_template_cache_on_save, sender=Template)
signals.pre_delete.connect(remove_cached_template, sender=Template)
m2m_changed.connect(
    invalidate_template_cache_on_sites_changed,
    sender=Template.sites.through,
)
