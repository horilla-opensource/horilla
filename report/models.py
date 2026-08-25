from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from horilla import horilla_middlewares
from horilla.models import HorillaModel
from horilla_auth.models import HorillaUser


class ReportTemplate(HorillaModel):
    """
    A saved field arrangement (Rows/Columns/renderer/aggregator) for a
    report's pivot table, or a shared/system layout for standard reports.
    """

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_COMPANY = "company"
    VISIBILITY_SYSTEM = "system"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, _("Private")),
        (VISIBILITY_COMPANY, _("Company")),
        (VISIBILITY_SYSTEM, _("System")),
    ]

    report_slug = models.CharField(max_length=100, verbose_name=_("Report"))
    name = models.CharField(max_length=100, verbose_name=_("Template Name"))
    config = models.JSONField(verbose_name=_("Field Arrangement"))
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE,
        verbose_name=_("Visibility"),
    )
    is_standard = models.BooleanField(
        default=False,
        verbose_name=_("Standard Report Layout"),
        help_text=_("Marks layouts seeded for standard enterprise reports."),
    )
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("report_slug", "name", "created_by", "company_id")

    def __str__(self):
        return f"{self.name} ({self.report_slug})"

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        selected_company = request.session.get("selected_company") if request else None
        if (
            not self.id
            and not self.company_id
            and selected_company
            and selected_company != "all"
        ):
            self.company_id = Company.find(selected_company)
        super().save(*args, **kwargs)


class ReportSubscription(HorillaModel):
    """
    Scheduled delivery of a standard report (Excel attachment via email).
    """

    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_MONTHLY = "monthly"
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, _("Daily")),
        (FREQUENCY_WEEKLY, _("Weekly")),
        (FREQUENCY_MONTHLY, _("Monthly")),
    ]

    report_slug = models.CharField(max_length=100, verbose_name=_("Report"))
    name = models.CharField(max_length=150, verbose_name=_("Subscription Name"))
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_WEEKLY,
        verbose_name=_("Frequency"),
    )
    recipients = models.TextField(
        verbose_name=_("Recipients"),
        help_text=_("Comma-separated email addresses."),
    )
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Filters"),
        help_text=_("Optional filter overrides (department_id, relative period)."),
    )
    last_run_at = models.DateTimeField(null=True, blank=True, editable=False)
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )
    owner = models.ForeignKey(
        HorillaUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_subscriptions",
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report Subscription")
        verbose_name_plural = _("Report Subscriptions")

    def __str__(self):
        return f"{self.name} ({self.report_slug})"

    def recipient_list(self) -> list[str]:
        return [
            email.strip()
            for email in (self.recipients or "").split(",")
            if email.strip()
        ]

    @property
    def report_name(self) -> str:
        from report.registry import get_report

        definition = get_report(self.report_slug)
        return str(definition.name) if definition else self.report_slug

    @property
    def frequency_label(self) -> str:
        return self.get_frequency_display()

    @property
    def status_label(self) -> str:
        return _("Active") if self.is_active else _("Paused")

    @property
    def status_slug(self) -> str:
        return "active" if self.is_active else "paused"

    @property
    def format_label(self) -> str:
        fmt = (self.filters or {}).get("format")
        return _("PDF") if fmt == "pdf" else _("Excel")

    def get_run_url(self):
        from django.urls import reverse

        return reverse("report-subscription-run", args=[self.pk])

    def get_toggle_url(self):
        from django.urls import reverse

        return reverse("report-subscription-toggle", args=[self.pk])

    def get_delete_url(self):
        from django.urls import reverse

        return reverse("report-subscription-delete", args=[self.pk])

    def get_edit_url(self):
        from django.urls import reverse

        return reverse("report-subscription-edit", args=[self.pk])

    def get_view_url(self):
        from django.urls import reverse

        return reverse("report-subscription-view", args=[self.pk])

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        selected_company = request.session.get("selected_company") if request else None
        if (
            not self.id
            and not self.company_id
            and selected_company
            and selected_company != "all"
        ):
            self.company_id = Company.find(selected_company)
        if request and not self.owner_id:
            self.owner = request.user
        super().save(*args, **kwargs)


class ReportFavorite(HorillaModel):
    """User-pinned standard report for quick catalog access."""

    report_slug = models.CharField(max_length=100, verbose_name=_("Report"))
    user = models.ForeignKey(
        HorillaUser,
        on_delete=models.CASCADE,
        related_name="report_favorites",
        verbose_name=_("User"),
    )
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report Favorite")
        verbose_name_plural = _("Report Favorites")
        unique_together = ("report_slug", "user", "company_id")

    def __str__(self):
        return f"{self.report_slug} ({self.user_id})"


class ReportSavedView(HorillaModel):
    """
    A user-named collection of standard reports for quick catalog filtering
    (e.g. "Q3 board pack") — distinct from ReportFavorite (a single implicit
    "pinned" set): a user can have any number of named views, each holding
    an arbitrary hand-picked set of reports.
    """

    name = models.CharField(max_length=100, verbose_name=_("View Name"))
    report_slugs = models.JSONField(default=list, blank=True, verbose_name=_("Reports"))
    owner = models.ForeignKey(
        HorillaUser,
        on_delete=models.CASCADE,
        related_name="report_saved_views",
        verbose_name=_("Owner"),
    )
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["name"]
        verbose_name = _("Report Saved View")
        verbose_name_plural = _("Report Saved Views")
        unique_together = ("name", "owner", "company_id")

    def __str__(self):
        return f"{self.name} ({self.owner_id})"

    def add_slugs(self, slugs: list[str]) -> None:
        current = list(self.report_slugs or [])
        for slug in slugs:
            if slug not in current:
                current.append(slug)
        self.report_slugs = current
        self.save(update_fields=["report_slugs"])

    def remove_slug(self, slug: str) -> None:
        current = [s for s in (self.report_slugs or []) if s != slug]
        self.report_slugs = current
        self.save(update_fields=["report_slugs"])


class ReportFilterPreset(HorillaModel):
    """Named filter snapshot for a standard report (period + advanced fields)."""

    report_slug = models.CharField(max_length=100, verbose_name=_("Report"))
    name = models.CharField(max_length=100, verbose_name=_("Preset Name"))
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Filters"),
        help_text=_("period_preset, dates, and report-specific filter keys."),
    )
    user = models.ForeignKey(
        HorillaUser,
        on_delete=models.CASCADE,
        related_name="report_filter_presets",
        verbose_name=_("User"),
    )
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["name"]
        verbose_name = _("Report Filter Preset")
        verbose_name_plural = _("Report Filter Presets")
        unique_together = ("report_slug", "name", "user", "company_id")

    def __str__(self):
        return f"{self.name} ({self.report_slug})"

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        selected_company = request.session.get("selected_company") if request else None
        if (
            not self.id
            and not self.company_id
            and selected_company
            and selected_company != "all"
        ):
            self.company_id = Company.find(selected_company)
        if request and not self.user_id:
            self.user = request.user
        super().save(*args, **kwargs)


class ReportRunLog(HorillaModel):
    """Lite audit of standard report runs (UI view / export)."""

    ACTION_VIEW = "view"
    ACTION_EXPORT = "export"
    ACTION_SUBSCRIBE = "subscribe"
    ACTION_CHOICES = [
        (ACTION_VIEW, _("View")),
        (ACTION_EXPORT, _("Export")),
        (ACTION_SUBSCRIBE, _("Subscription")),
    ]

    report_slug = models.CharField(max_length=100, verbose_name=_("Report"))
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default=ACTION_VIEW,
        verbose_name=_("Action"),
    )
    filters = models.JSONField(default=dict, blank=True, verbose_name=_("Filters"))
    user = models.ForeignKey(
        HorillaUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_run_logs",
        verbose_name=_("User"),
    )
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    @property
    def report_name(self) -> str:
        from report.registry import get_report

        definition = get_report(self.report_slug)
        return str(definition.name) if definition else self.report_slug

    @property
    def format_label(self) -> str:
        return ((self.filters or {}).get("format") or "").upper()

    @property
    def company_label(self) -> str:
        return str(self.company_id) if self.company_id_id else ""

    @property
    def employee_label(self) -> str:
        """Employee name (e.g. "Adam Admin (PEP00)") instead of the raw
        HorillaUser username — more recognizable to HR admins reading the
        audit trail, who think in terms of employees, not login names."""
        if not self.user_id:
            return ""
        employee = getattr(self.user, "employee_get", None)
        if employee:
            return str(employee)
        return self.user.get_full_name() or self.user.username

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report Run Log")
        verbose_name_plural = _("Report Run Logs")
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="report_runlog_user_created",
            ),
            models.Index(
                fields=["report_slug", "-created_at"],
                name="report_runlog_slug_created",
            ),
        ]

    def __str__(self):
        return f"{self.report_slug} · {self.action}"


class ReportAccess(HorillaModel):
    """
    Optional access matrix for standard reports.

    When no rows match a report for the user, Django definition.permission
    (+ has_export_access for exports) remains the fallback.
    When rows match, can_view / can_export / can_subscribe gate the action.
    """

    report_slug = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Report slug"),
        help_text=_("Leave blank to apply to a whole domain (or all reports)."),
    )
    domain = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Domain"),
        help_text=_("workforce, time_leave, payroll, talent, compliance — or blank."),
    )
    group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="report_access_rules",
        verbose_name=_("Group"),
        help_text=_("Blank = any authenticated user (still subject to permission)."),
    )
    permission = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name=_("Permission"),
        help_text=_(
            "Optional Django permission codename, e.g. employee.view_employee."
        ),
    )
    can_view = models.BooleanField(default=True, verbose_name=_("Can view"))
    can_export = models.BooleanField(default=True, verbose_name=_("Can export"))
    can_subscribe = models.BooleanField(default=True, verbose_name=_("Can subscribe"))
    company_id = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["report_slug", "domain", "group_id"]
        verbose_name = _("Report Access")
        verbose_name_plural = _("Report Access")

    def __str__(self):
        target = self.report_slug or self.domain or "*"
        group = self.group.name if self.group_id else "*"
        return f"{target} · {group}"
