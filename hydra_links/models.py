from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from hydra.models import HydraModel
from hydra_coordination.models import Location
from hydra_links.public_urls import validate_public_hydra_url


class PublicHydraLink(HydraModel):
    class Kind(models.TextChoices):
        ARRIVAL_GUIDANCE = "arrival", _("Arrival guidance")
        LOCATION_TRAINING = "training", _("Location training")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="public_hydra_links",
        null=True,
        blank=True,
        verbose_name=_("Location"),
    )
    label = models.CharField(max_length=120, verbose_name=_("Public label"))
    base_url = models.URLField(max_length=500, verbose_name=_("Public HTTPS URL"))
    order = models.PositiveSmallIntegerField(default=100, verbose_name=_("Order"))

    class Meta:
        ordering = ("kind", "order", "location__name", "label", "pk")
        permissions = (
            (
                "manage_global_publichydralink",
                "Can manage global Hydra public links",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=(
                    Q(kind="arrival", location__isnull=True)
                    | Q(kind="training", location__isnull=False)
                ),
                name="hyd_link_kind_location_valid",
            ),
            models.UniqueConstraint(
                fields=("kind",),
                condition=Q(location__isnull=True),
                name="hyd_link_global_kind_uniq",
            ),
            models.UniqueConstraint(
                fields=("kind", "location"),
                condition=Q(location__isnull=False),
                name="hyd_link_location_kind_uniq",
            ),
        )
        indexes = (
            models.Index(
                fields=("location", "is_active"),
                name="hyd_link_location_active_idx",
            ),
        )

    def __str__(self):
        scope = self.location or _("Global")
        return f"{scope} / {self.label}"

    def clean(self):
        super().clean()
        self.label = " ".join(self.label.split())
        self.base_url = self.base_url.strip()
        validate_public_hydra_url(self.base_url)
        if self.kind == self.Kind.ARRIVAL_GUIDANCE and self.location_id:
            raise ValidationError(
                {"location": _("Arrival guidance must be global.")}
            )
        if self.kind == self.Kind.LOCATION_TRAINING and not self.location_id:
            raise ValidationError(
                {"location": _("Location training requires a Location.")}
            )

    def get_absolute_url(self):
        return reverse("hydra-public-link-update", kwargs={"link_uuid": self.uuid})
