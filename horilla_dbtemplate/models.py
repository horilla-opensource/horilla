"""
Template model compatible with django-dbtemplates schema.

New features added:
- TemplateVersion: full content snapshot on every save + restore support
- state: draft / active / archived  (only active templates are served)
- active_from / active_until: scheduled activation window
- language: per-language override (e.g. "ar", "fr")
- tags: comma-separated tags for grouping/filtering
- locked_by / locked_at: soft edit-lock to prevent concurrent edits
- access_count / last_accessed_at: usage analytics
- clean(): syntax validation before every save
"""

from auditlog.models import AuditlogHistoryField
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.template import Template as DjangoTemplate
from django.template import TemplateSyntaxError
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from horilla.horilla_middlewares import _thread_locals

from .conf import AUTO_POPULATE_CONTENT


def get_template_source(name):
    """Load template source from non-db loaders (filesystem, app_directories)."""
    from django.template import TemplateDoesNotExist
    from django.template.loader import _engine_list

    for engine in _engine_list():
        for loader in engine.engine.template_loaders:
            if loader.__module__.startswith("."):
                continue
            for origin in loader.get_template_sources(name):
                try:
                    return loader.get_contents(origin)
                except (NotImplementedError, TemplateDoesNotExist):
                    continue
    return None


STATE_DRAFT = "draft"
STATE_ACTIVE = "active"
STATE_ARCHIVED = "archived"

STATE_CHOICES = [
    (STATE_DRAFT, _("Draft")),
    (STATE_ACTIVE, _("Active")),
    (STATE_ARCHIVED, _("Archived")),
]

LOCK_TIMEOUT_MINUTES = 30


class Template(models.Model):
    """
    Database-stored template.

    name       : template path (e.g. "flatpages/default.html")
    content    : template body
    state      : draft / active / archived
    sites      : optional M2M; empty = global
    language   : optional language code for per-language overrides
    tags       : comma-separated tags
    active_from / active_until : scheduling window
    locked_by / locked_at      : soft edit-lock
    access_count / last_accessed_at : analytics
    """

    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("Example: 'flatpages/default.html'"),
    )
    content = models.TextField(_("content"), blank=True)

    state = models.CharField(
        _("state"),
        max_length=20,
        choices=STATE_CHOICES,
        default=STATE_ACTIVE,
        db_index=True,
        help_text=_("Only ACTIVE templates are served by the DB template loader."),
    )

    sites = models.ManyToManyField(
        Site,
        verbose_name=_("sites"),
        blank=True,
        related_name="horilla_dbtemplate_templates",
    )

    language = models.CharField(
        _("language"),
        max_length=10,
        blank=True,
        db_index=True,
        help_text=_(
            "Optional language code (e.g. 'ar', 'fr'). Leave blank for all languages."
        ),
    )

    tags = models.CharField(
        _("tags"),
        max_length=255,
        blank=True,
        help_text=_("Comma-separated tags. E.g. 'email,onboarding,pdf'"),
    )

    active_from = models.DateTimeField(
        _("active from"),
        null=True,
        blank=True,
        help_text=_(
            "Serve this template only after this datetime. Leave blank = no restriction."
        ),
    )
    active_until = models.DateTimeField(
        _("active until"),
        null=True,
        blank=True,
        help_text=_(
            "Stop serving this template after this datetime. Leave blank = no restriction."
        ),
    )

    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_locked",
        verbose_name=_("Locked By"),
    )
    locked_at = models.DateTimeField(_("Locked At"), null=True, blank=True)

    access_count = models.PositiveIntegerField(
        _("Access Count"), default=0, editable=False
    )
    last_accessed_at = models.DateTimeField(
        _("Last Accessed At"), null=True, blank=True, editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated",
        verbose_name=_("Updated By"),
    )
    history = AuditlogHistoryField()

    objects = models.Manager()
    on_site = CurrentSiteManager("sites")

    class Meta:
        """DB table name, labels, and default ordering for :class:`Template`."""

        verbose_name = _("Template")
        verbose_name_plural = _("Templates")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def populate(self, name=None):
        """Populate content from filesystem/app loader if found."""
        name = name or self.name
        try:
            source = get_template_source(name)
            if source:
                self.content = source
        except Exception:
            pass

    def is_schedulable_active(self):
        """Return True if within the scheduled activation window."""
        current = now()
        if self.active_from and current < self.active_from:
            return False
        if self.active_until and current > self.active_until:
            return False
        return True

    def is_locked(self):
        """Return True if locked by a user and the lock has not timed out."""
        if not self.locked_by or not self.locked_at:
            return False
        from datetime import timedelta

        timeout = self.locked_at + timedelta(minutes=LOCK_TIMEOUT_MINUTES)
        return now() < timeout

    def lock(self, user):
        """Acquire edit lock for user (DB-level update)."""
        Template.objects.filter(pk=self.pk).update(locked_by=user, locked_at=now())
        self.locked_by = user
        self.locked_at = now()

    def unlock(self):
        """Release edit lock."""
        Template.objects.filter(pk=self.pk).update(locked_by=None, locked_at=None)
        self.locked_by = None
        self.locked_at = None

    def clean(self):
        """Validate template syntax and scheduling window."""
        if self.content:
            try:
                DjangoTemplate(self.content)
            except TemplateSyntaxError as e:
                raise ValidationError(
                    {
                        "content": _("Template syntax error: %(error)s")
                        % {"error": str(e)}
                    }
                ) from e

        if self.active_from and self.active_until:
            if self.active_from >= self.active_until:
                raise ValidationError(
                    {"active_until": _("'Active until' must be after 'Active from'.")}
                )

    def save(self, *args, **kwargs):
        """Persist with thread-local user tracking, optional autopopulate, and version snapshot."""
        user = None
        request = getattr(_thread_locals, "request", None)
        if request:
            user = getattr(request, "user", None)

        is_new = not self.pk

        if is_new:
            if user and not isinstance(user, AnonymousUser):
                self.created_by = user
                self.updated_by = user
        else:
            if user and not isinstance(user, AnonymousUser):
                self.updated_by = user

        if AUTO_POPULATE_CONTENT and not self.content:
            self.populate()

        skip_validation = kwargs.pop("skip_validation", False)
        if not skip_validation:
            self.full_clean()

        super().save(*args, **kwargs)
        self._snapshot_version(user=user)

    def _snapshot_version(self, user=None):
        """Create a TemplateVersion snapshot if content/state changed."""
        last = self.versions.order_by("-version").first()
        last_version_num = last.version if last else 0
        if last and last.content == self.content and last.state == self.state:
            return
        TemplateVersion.objects.create(
            template=self,
            version=last_version_num + 1,
            content=self.content,
            state=self.state,
            created_by=user,
        )

    def restore_version(self, version_number, user=None):
        """Restore content from a specific version snapshot."""
        version = self.versions.get(version=version_number)
        self.content = version.content
        self.save(skip_validation=True)

    def get_tags_list(self):
        """Return tags as a Python list."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class TemplateVersion(models.Model):
    """
    Immutable content snapshot of a Template.

    Created automatically on every Template.save() when content or state changes.
    Restore via Template.restore_version(version_number).
    """

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name=_("template"),
    )
    version = models.PositiveIntegerField(_("version"), db_index=True)
    content = models.TextField(_("content"), blank=True)
    state = models.CharField(
        _("state"),
        max_length=20,
        choices=STATE_CHOICES,
        default=STATE_ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )

    class Meta:
        """DB metadata and uniqueness of ``(template, version)`` for snapshots."""

        verbose_name = _("Template Version")
        verbose_name_plural = _("Template Versions")
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(
                fields=("template", "version"),
                name="horilla_dbtemplate_unique_template_version",
            )
        ]

    def __str__(self):
        return f"{self.template.name} — v{self.version}"
