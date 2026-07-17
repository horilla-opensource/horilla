from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company, Department
from hydra.models import HorillaModel
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


class TerminationMode(models.TextChoices):
    NONE = "", _("Not terminated")
    SCHEDULED = "scheduled", _("Scheduled end")
    IMMEDIATE = "immediate", _("Immediate revocation")


class ScopeGrant(HorillaModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_scope_grants",
        verbose_name=_("User"),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hydra_scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Department"),
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Location"),
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Section / stage"),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="scope_grants",
        null=True,
        blank=True,
        verbose_name=_("Team"),
    )
    valid_from = models.DateField(default=timezone.localdate, verbose_name=_("Valid from"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))
    termination_mode = models.CharField(
        max_length=16,
        choices=TerminationMode.choices,
        default=TerminationMode.NONE,
        blank=True,
        editable=False,
    )
    termination_reason = models.CharField(max_length=255, blank=True, editable=False)
    termination_recorded_at = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    termination_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_scope_terminations_recorded",
        null=True,
        blank=True,
        editable=False,
    )

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
            models.CheckConstraint(
                check=(
                    Q(
                        termination_mode="",
                        termination_reason="",
                        termination_recorded_at__isnull=True,
                        termination_recorded_by__isnull=True,
                    )
                    | (
                        Q(
                            termination_mode__in=(
                                TerminationMode.SCHEDULED,
                                TerminationMode.IMMEDIATE,
                            ),
                            termination_recorded_at__isnull=False,
                            termination_recorded_by__isnull=False,
                        )
                        & ~Q(termination_reason="")
                    )
                ),
                name="hydra_scope_termination_audit",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(termination_mode=TerminationMode.SCHEDULED)
                    | Q(valid_until__isnull=False)
                ),
                name="hydra_scope_scheduled_end_date",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(termination_mode=TerminationMode.IMMEDIATE)
                    | Q(is_active=False)
                ),
                name="hydra_scope_immediate_inactive",
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

    @property
    def state_label(self):
        day = timezone.localdate()
        if self.termination_mode == TerminationMode.IMMEDIATE:
            return _("Revoked")
        if not self.is_active:
            return _("Inactive")
        if self.valid_from > day:
            return _("Scheduled")
        if self.valid_until is not None and self.valid_until < day:
            return _("Ended")
        if self.termination_mode == TerminationMode.SCHEDULED:
            return _("End scheduled")
        return _("Current")

    @property
    def can_terminate(self):
        day = timezone.localdate()
        return self.is_active and (
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
    termination_mode = models.CharField(
        max_length=16,
        choices=TerminationMode.choices,
        default=TerminationMode.NONE,
        blank=True,
        editable=False,
    )
    termination_reason = models.CharField(max_length=255, blank=True, editable=False)
    termination_recorded_at = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    termination_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_assignment_terminations_recorded",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ("-valid_from", "-pk")
        constraints = (
            models.CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gte=F("valid_from")),
                name="hydra_assignment_valid_dates",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        termination_mode="",
                        termination_reason="",
                        termination_recorded_at__isnull=True,
                        termination_recorded_by__isnull=True,
                    )
                    | (
                        Q(
                            termination_mode__in=(
                                TerminationMode.SCHEDULED,
                                TerminationMode.IMMEDIATE,
                            ),
                            termination_recorded_at__isnull=False,
                            termination_recorded_by__isnull=False,
                        )
                        & ~Q(termination_reason="")
                    )
                ),
                name="hydra_assignment_termination_audit",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(termination_mode=TerminationMode.SCHEDULED)
                    | Q(valid_until__isnull=False)
                ),
                name="hydra_assignment_scheduled_end_date",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(termination_mode=TerminationMode.IMMEDIATE)
                    | Q(is_active=False)
                ),
                name="hydra_assignment_immediate_inactive",
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
        if self.termination_mode == TerminationMode.IMMEDIATE:
            return _("Ended immediately")
        if not self.is_active:
            return _("Replaced")
        if self.valid_from > day:
            return _("Scheduled")
        if self.valid_until is not None and self.valid_until < day:
            return _("Ended")
        if self.termination_mode == TerminationMode.SCHEDULED:
            return _("End scheduled")
        return _("Current")

    @property
    def can_terminate(self):
        day = timezone.localdate()
        return self.is_active and (
            self.valid_until is None or self.valid_until >= day
        )


class OrganizationAccessEventQuerySet(models.QuerySet):
    DELIVERY_FIELDS = {
        "notification_status",
        "notification_attempts",
        "notification_last_attempt_at",
        "notification_error_code",
        "notification",
    }

    def update(self, **kwargs):
        if set(kwargs) - self.DELIVERY_FIELDS:
            raise TypeError("Organization access event facts are append-only.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Organization access events are append-only.")


class OrganizationAccessEvent(models.Model):
    class Action(models.TextChoices):
        SCOPE_END_SCHEDULED = "scope_end_scheduled", _("Scope end scheduled")
        SCOPE_REVOKED = "scope_revoked", _("Scope revoked")
        ASSIGNMENT_END_SCHEDULED = (
            "assignment_end_scheduled",
            _("Assignment end scheduled"),
        )
        ASSIGNMENT_ENDED = "assignment_ended", _("Assignment ended")

    class NotificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    scope_grant = models.ForeignKey(
        ScopeGrant,
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
        null=True,
        blank=True,
    )
    person_assignment = models.ForeignKey(
        PersonAssignment,
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_organization_access_events",
    )
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_organization_access_events_received",
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=255)
    effective_until = models.DateField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    notification_attempts = models.PositiveSmallIntegerField(default=0)
    notification_last_attempt_at = models.DateTimeField(null=True, blank=True)
    notification_error_code = models.CharField(max_length=80, blank=True)
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.PROTECT,
        related_name="hydra_organization_access_events",
        null=True,
        blank=True,
    )

    objects = OrganizationAccessEventQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_organizationaccessevent", "Can view organization access events"),
        )
        constraints = (
            models.CheckConstraint(
                check=(
                    Q(scope_grant__isnull=False, person_assignment__isnull=True)
                    | Q(scope_grant__isnull=True, person_assignment__isnull=False)
                ),
                name="hydra_access_event_one_subject",
            ),
            models.CheckConstraint(
                check=~Q(reason=""),
                name="hydra_access_event_reason_required",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        action__in=(
                            "scope_end_scheduled",
                            "scope_revoked",
                        ),
                        scope_grant__isnull=False,
                        person_assignment__isnull=True,
                    )
                    | Q(
                        action__in=(
                            "assignment_end_scheduled",
                            "assignment_ended",
                        ),
                        scope_grant__isnull=True,
                        person_assignment__isnull=False,
                    )
                ),
                name="hydra_access_event_action_subject",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        action__in=(
                            "scope_end_scheduled",
                            "assignment_end_scheduled",
                        ),
                        effective_until__isnull=False,
                    )
                    | Q(
                        action__in=(
                            "scope_revoked",
                            "assignment_ended",
                        ),
                        effective_until__isnull=True,
                    )
                ),
                name="hydra_access_event_effective_date",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        subject_user__isnull=True,
                        notification_status="not_applicable",
                    )
                    | (
                        Q(subject_user__isnull=False)
                        & ~Q(
                            notification_status="not_applicable"
                        )
                    )
                ),
                name="hydra_access_event_notify_target",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(notification_status="sent")
                    | Q(notification__isnull=False)
                ),
                name="hydra_access_event_sent_record",
            ),
        )
        indexes = (
            models.Index(
                fields=("notification_status", "occurred_at"),
                name="hydra_access_notify_idx",
            ),
        )

    CORE_FIELDS = (
        "scope_grant_id",
        "person_assignment_id",
        "action",
        "actor_id",
        "subject_user_id",
        "reason",
        "effective_until",
        "occurred_at",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.values(*self.CORE_FIELDS).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.CORE_FIELDS):
                raise TypeError("Organization access event facts are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Organization access events are append-only.")
