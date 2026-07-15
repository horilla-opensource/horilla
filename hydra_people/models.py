from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla.models import HorillaModel
from recruitment.models import Candidate


phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ()-]{7,25}$",
    message=_("Enter a valid phone number."),
)
citizenship_validator = RegexValidator(
    regex=r"^[A-Za-z]{2}$",
    message=_("Use a two-letter ISO country code, for example UA or PL."),
)


class Person(HorillaModel):
    class Gender(models.TextChoices):
        FEMALE = "female", _("Female")
        MALE = "male", _("Male")
        OTHER = "other", _("Other")
        UNSPECIFIED = "unspecified", _("Unspecified")

    class PreferredLanguage(models.TextChoices):
        POLISH = "pl", _("Polish")
        RUSSIAN = "ru", _("Russian")
        UKRAINIAN = "uk", _("Ukrainian")
        ENGLISH = "en", _("English")
        AZERBAIJANI = "az", _("Azerbaijani")
        SPANISH = "es", _("Spanish")
        FILIPINO = "fil", _("Filipino")
        INDONESIAN = "id", _("Indonesian")
        NEPALI = "ne", _("Nepali")

    class LifecycleState(models.TextChoices):
        PROSPECT = "prospect", _("Prospect")
        CANDIDATE = "candidate", _("Candidate")
        ONBOARDING = "onboarding", _("Onboarding")
        EMPLOYEE = "employee", _("Employee")
        INACTIVE = "inactive", _("Inactive")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    hydra_id = models.CharField(max_length=24, unique=True, editable=False)
    passport_name = models.CharField(max_length=255, verbose_name=_("Passport name"))
    first_name = models.CharField(max_length=100, verbose_name=_("First name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last name"))
    date_of_birth = models.DateField(verbose_name=_("Date of birth"))
    gender = models.CharField(
        max_length=16,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
        verbose_name=_("Gender"),
    )
    citizenship = models.CharField(
        max_length=2,
        validators=[citizenship_validator],
        verbose_name=_("Citizenship"),
        help_text=_("Two-letter ISO country code."),
    )
    preferred_language = models.CharField(
        max_length=3,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.POLISH,
        verbose_name=_("Preferred language"),
    )
    phone = models.CharField(
        max_length=25,
        blank=True,
        validators=[phone_validator],
        verbose_name=_("Phone"),
    )
    whatsapp_viber = models.CharField(
        max_length=25,
        blank=True,
        validators=[phone_validator],
        verbose_name=_("WhatsApp / Viber"),
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    lifecycle_state = models.CharField(
        max_length=16,
        choices=LifecycleState.choices,
        default=LifecycleState.PROSPECT,
        verbose_name=_("Lifecycle state"),
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hydra_person",
        verbose_name=_("Employee"),
    )

    class Meta:
        ordering = ("passport_name", "hydra_id")
        verbose_name = _("Hydra person")
        verbose_name_plural = _("Hydra people")
        permissions = (
            ("link_candidate", "Can link recruitment applications to Hydra person"),
            (
                "convert_person_to_employee",
                "Can convert Hydra person to Horilla employee",
            ),
        )
        indexes = (
            models.Index(fields=("last_name", "first_name"), name="hydra_person_name_idx"),
            models.Index(fields=("date_of_birth", "citizenship"), name="hydra_person_identity_idx"),
        )

    def __str__(self):
        return f"{self.hydra_id} — {self.passport_name}"

    def clean(self):
        super().clean()
        for field_name in ("passport_name", "first_name", "last_name"):
            value = getattr(self, field_name, "")
            setattr(self, field_name, " ".join(value.split()))
        self.citizenship = self.citizenship.strip().upper()
        self.email = self.email.strip().lower()
        self.phone = self.phone.strip()
        self.whatsapp_viber = self.whatsapp_viber.strip()

    def save(self, *args, **kwargs):
        if not self.hydra_id:
            self.hydra_id = f"HYD-{self.uuid.hex[:16].upper()}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("hydra-person-detail", kwargs={"person_uuid": self.uuid})


class AppendOnlyConversionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Employee conversion history is append-only.")

    def delete(self):
        raise TypeError("Employee conversion history is append-only.")


class EmployeeConversion(models.Model):
    class Source(models.TextChoices):
        HYDRA_OPERATOR = "hydra_operator", _("Hydra operator")
        HORILLA_ONBOARDING = "horilla_onboarding", _("Horilla onboarding")

    person = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="employee_conversion",
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_employee_conversion",
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.PROTECT,
        related_name="hydra_conversion",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_employee_conversions",
    )
    source = models.CharField(max_length=24, choices=Source.choices)
    source_snapshot = models.JSONField()
    field_decisions = models.JSONField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyConversionQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_employeeconversion", "Can view employee conversion history"),
        )
        indexes = (
            models.Index(fields=("occurred_at",), name="hyd_people_conv_time_idx"),
        )

    def __str__(self):
        return f"{self.person.hydra_id} -> {self.employee}"

    def clean(self):
        super().clean()
        if self.person_id and self.employee_id:
            if self.person.employee_id != self.employee_id:
                raise ValidationError(
                    {"employee": _("The employee must be linked to this Person.")}
                )
        if self.candidate_id and self.person_id:
            try:
                linked_person_id = self.candidate.hydra_person_link.person_id
            except PersonApplication.DoesNotExist as error:
                raise ValidationError(
                    {"candidate": _("The application must be linked to a Person.")}
                ) from error
            if linked_person_id != self.person_id:
                raise ValidationError(
                    {"candidate": _("The application belongs to another Person.")}
                )
        if self.candidate_id and self.employee_id:
            if self.candidate.converted_employee_id_id != self.employee_id:
                raise ValidationError(
                    {"candidate": _("The application must reference this employee.")}
                )
        if not self.source_snapshot or not self.field_decisions:
            raise ValidationError(_("Conversion audit data cannot be empty."))

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Employee conversion history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Employee conversion history is append-only.")


class PersonApplication(HorillaModel):
    class LinkSource(models.TextChoices):
        MANUAL = "manual", _("Manual link")
        HYDRA_INTAKE = "hydra_intake", _("Hydra intake")
        BACKFILL = "backfill", _("Backfill")

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name=_("Person"),
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_person_link",
        verbose_name=_("Candidate application"),
    )
    link_source = models.CharField(
        max_length=16,
        choices=LinkSource.choices,
        default=LinkSource.MANUAL,
        verbose_name=_("Link source"),
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = _("Person application link")
        verbose_name_plural = _("Person application links")

    def __str__(self):
        return f"{self.person.hydra_id} ↔ {self.candidate}"
