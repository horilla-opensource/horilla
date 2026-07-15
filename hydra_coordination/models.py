from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company, Department
from horilla.models import HorillaModel
from hydra_people.models import Person


class Location(HorillaModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_locations",
        verbose_name=_("Company"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Location"))
    code = models.CharField(max_length=20, verbose_name=_("Code"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("Address"))

    class Meta:
        ordering = ("company__company", "name")
        permissions = (
            ("view_coordinator_panel", "Can view the Hydra coordinator panel"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code"), name="hydra_location_company_code_uniq"
            ),
            models.UniqueConstraint(
                fields=("company", "name"), name="hydra_location_company_name_uniq"
            ),
        )

    def __str__(self):
        return f"{self.company} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.code = self.code.strip().upper()
        self.address = " ".join(self.address.split())


class Section(HorillaModel):
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="sections",
        verbose_name=_("Location"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hydra_sections",
        null=True,
        blank=True,
        verbose_name=_("Department"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Section / stage"))
    code = models.CharField(max_length=20, verbose_name=_("Code"))

    class Meta:
        ordering = ("location__company__company", "location__name", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("location", "code"), name="hydra_section_location_code_uniq"
            ),
            models.UniqueConstraint(
                fields=("location", "name"), name="hydra_section_location_name_uniq"
            ),
        )

    def __str__(self):
        return f"{self.location} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.code = self.code.strip().upper()
        if (
            self.location_id
            and self.department_id
            and not self.department.company_id.filter(pk=self.location.company_id).exists()
        ):
            raise ValidationError(
                {"department": _("Department must belong to the location company.")}
            )


class Team(HorillaModel):
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="teams",
        verbose_name=_("Section / stage"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Team"))
    code = models.CharField(max_length=20, verbose_name=_("Code"))

    class Meta:
        ordering = (
            "section__location__company__company",
            "section__location__name",
            "section__name",
            "name",
        )
        permissions = (
            ("view_brigadier_panel", "Can view the Hydra brigadier panel"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("section", "code"), name="hydra_team_section_code_uniq"
            ),
            models.UniqueConstraint(
                fields=("section", "name"), name="hydra_team_section_name_uniq"
            ),
        )

    def __str__(self):
        return f"{self.section} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.code = self.code.strip().upper()


class ScopeGrant(HorillaModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hydra_scope_grants",
        verbose_name=_("User"),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hydra_scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="hydra_scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Department"),
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Location"),
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Section / stage"),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Team"),
    )
    valid_from = models.DateField(default=timezone.localdate, verbose_name=_("Valid from"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))

    class Meta:
        ordering = ("user__username", "valid_from", "pk")
        constraints = (
            models.CheckConstraint(
                check=(
                    Q(company__isnull=False, department__isnull=True, location__isnull=True, section__isnull=True, team__isnull=True)
                    | Q(company__isnull=True, department__isnull=False, location__isnull=True, section__isnull=True, team__isnull=True)
                    | Q(company__isnull=True, department__isnull=True, location__isnull=False, section__isnull=True, team__isnull=True)
                    | Q(company__isnull=True, department__isnull=True, location__isnull=True, section__isnull=False, team__isnull=True)
                    | Q(company__isnull=True, department__isnull=True, location__isnull=True, section__isnull=True, team__isnull=False)
                ),
                name="hydra_scope_exactly_one_target",
            ),
            models.CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gte=F("valid_from")),
                name="hydra_scope_valid_dates",
            ),
        )

    def __str__(self):
        return f"{self.user} / {self.scope_type}: {self.target}"

    @property
    def scope_type(self):
        for field_name in ("company", "department", "location", "section", "team"):
            if getattr(self, f"{field_name}_id"):
                return field_name
        return ""

    @property
    def target(self):
        return getattr(self, self.scope_type, None)

    def is_current(self, day=None):
        day = day or timezone.localdate()
        return self.is_active and self.valid_from <= day and (
            self.valid_until is None or self.valid_until >= day
        )

class PersonAssignment(HorillaModel):
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="coordination_assignments",
        verbose_name=_("Person"),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="person_assignments",
        verbose_name=_("Team"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hydra_person_assignments",
        verbose_name=_("Department"),
    )
    valid_from = models.DateField(default=timezone.localdate, verbose_name=_("Valid from"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))
    is_primary = models.BooleanField(default=True, verbose_name=_("Primary assignment"))

    class Meta:
        ordering = ("-valid_from", "-pk")
        constraints = (
            models.CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gte=F("valid_from")),
                name="hydra_assignment_valid_dates",
            ),
        )
        permissions = (
            ("assign_person", "Can assign a Hydra person to an organization team"),
        )

    def __str__(self):
        return f"{self.person} / {self.team}"

    def clean(self):
        super().clean()
        if (
            self.team_id
            and self.department_id
            and not self.department.company_id.filter(
                pk=self.team.section.location.company_id
            ).exists()
        ):
            raise ValidationError(
                {"department": _("Department must belong to the team company.")}
            )

    def is_current(self, day=None):
        day = day or timezone.localdate()
        return self.is_active and self.valid_from <= day and (
            self.valid_until is None or self.valid_until >= day
        )

    @property
    def state_label(self):
        day = timezone.localdate()
        if not self.is_active:
            return _("Replaced")
        if self.valid_from > day:
            return _("Scheduled")
        if self.valid_until is not None and self.valid_until < day:
            return _("Ended")
        return _("Current")
