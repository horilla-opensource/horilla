import re
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra.models import HydraModel
from hydra_templates.placeholders import placeholder_names


class MessageTemplate(HydraModel):
    class Language(models.TextChoices):
        POLISH = "pl", _("Polish")
        UKRAINIAN = "uk", _("Ukrainian")
        RUSSIAN = "ru", _("Russian")
        ENGLISH = "en", _("English")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_message_templates",
        verbose_name=_("Company"),
    )
    code = models.CharField(max_length=64, verbose_name=_("Stable code"))
    name = models.CharField(max_length=160, verbose_name=_("Name"))
    language = models.CharField(
        max_length=3,
        choices=Language.choices,
        default=Language.POLISH,
        verbose_name=_("Language"),
    )
    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    body = models.TextField(max_length=10000, verbose_name=_("Plain-text body"))

    class Meta:
        ordering = ("company__company", "code", "language", "pk")
        permissions = (
            ("export_template_data", "Can export scoped Szablonizator data"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code", "language"),
                name="hyd_tpl_company_code_lang_uniq",
            ),
        )
        indexes = (
            models.Index(fields=("company", "is_active"), name="hyd_tpl_company_active_idx"),
        )

    def __str__(self):
        return f"{self.company} / {self.code} [{self.language}]"

    def clean(self):
        super().clean()
        self.code = self.code.strip().upper()
        self.name = " ".join(self.name.split())
        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,63}", self.code):
            raise ValidationError(
                {
                    "code": _(
                        "Use 2-64 uppercase ASCII letters, digits, underscores or hyphens; start with a letter."
                    )
                }
            )
        errors = {}
        for field_name in ("subject", "body"):
            try:
                placeholder_names(getattr(self, field_name))
            except ValidationError as error:
                errors[field_name] = error.messages
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return reverse("hydra-template-update", kwargs={"template_uuid": self.uuid})


class AppendOnlyExportQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Template data export history is append-only.")
    def delete(self):
        raise TypeError("Template data export history is append-only.")


class TemplateDataExport(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_template_data_exports",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    row_count = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    filters = models.JSONField(default=dict)
    scope_company_ids = models.JSONField(default=list)

    objects = AppendOnlyExportQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_templatedataexport", "Can view template data export audit"),
        )
        indexes = (
            models.Index(fields=("actor", "occurred_at"), name="hyd_tpl_export_actor_idx"),
        )

    def __str__(self):
        return f"{self.filename} / {self.row_count} / {self.sha256[:12]}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Template data export history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Template data export history is append-only.")
