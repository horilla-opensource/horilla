"""CBV-based Report Subscriptions list — self-service, owner-scoped."""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from report.access import company_id_from_request, user_can_subscribe_report
from report.forms import ReportSubscriptionForm
from report.models import ReportSubscription
from report.registry import DOMAIN_LABELS, get_report, reports_by_domain


@method_decorator(login_required, name="dispatch")
class ReportSubscriptionsView(TemplateView):
    """Thin page shell — HTMX-loads the Nav and List fragments below."""

    template_name = "cbv/subscriptions/subscriptions_home.html"


@method_decorator(login_required, name="dispatch")
class ReportSubscriptionsNav(HorillaNavView):
    nav_title = _("Report Subscriptions")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("report-subscriptions-list")
        self.search_swap_target = "#listContainer"
        # Subscriptions used to only be creatable from a report's detail
        # page (Subscribe modal) — that page is hidden for now, so this is
        # the only remaining entry point; the picker view lets the user
        # choose which report to subscribe to since there's no report
        # context on this list page.
        self.create_attrs = f"""
            onclick="event.stopPropagation();"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            hx-target="#genericModalBody"
            hx-get="{reverse('report-subscription-create')}"
        """


@method_decorator(login_required, name="dispatch")
class ReportSubscriptionsListView(HorillaListView):
    """
    Every user only ever sees/manages their own subscriptions — matches the
    ownership scoping the previous function-based view enforced.
    """

    model = ReportSubscription
    # True (not False) is what actually unlocks the checkbox column that
    # both the colored row_status_class border-div and the
    # row_status_indications pills below render inside of — see
    # horilla_views/templates/generic/horilla_list_table.html lines 32-34 /
    # 131-155. It does not add any bulk-delete/bulk-update UI on its own
    # (those are separately gated by bulk_path/quick_export, both unset
    # here), matching payroll's Payslip list, whose own status pills use
    # the exact same mechanism (payroll/cbv/payslip.py).
    bulk_select_option = True
    row_status_class = "status-{status_slug}"

    columns = [
        (_("Subscription"), "name"),
        (_("Report"), "report_name"),
        (_("Frequency"), "frequency_label"),
        (_("Recipients"), "recipients"),
        (_("Status"), "status_label"),
        (_("Last sent"), "last_run_at"),
    ]

    # Clicking anywhere on the row opens the detail view — matches the same
    # convention used across the app (Asset, Contracts, Holidays, Loans,
    # Leave Requests, etc: hx-get + data-toggle="oh-modal-toggle" targeting
    # #genericModal). The action-column buttons below are already shielded
    # from this by the framework's own onclick="event.stopPropagation()"
    # on that <td> — no extra wiring needed.
    row_attrs = """
        hx-get="{get_view_url}"
        hx-target="#genericModalBody"
        data-toggle="oh-modal-toggle"
        data-target="#genericModal"
        class="cursor-pointer"
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "reportSubscriptions"
        self.search_url = reverse("report-subscriptions-list")
        # Quick status filter pills — same visual/interaction convention as
        # payroll's Payslip list, adapted since this list has no
        # filter_class/form of its own to drive: each pill just re-fetches
        # the list with a `status` query param that get_queryset() below
        # reads directly, rather than Payslip's "set a hidden filter-form
        # field, then click Apply" mechanism.
        self.row_status_indications = [
            (
                "active--dot",
                _("Active"),
                f"""
                onclick="htmx.ajax('GET', '{self.search_url}?status=active',
                    {{target: '#{self.view_id}', swap: 'outerHTML'}});"
                """,
            ),
            (
                "paused--dot",
                _("Paused"),
                f"""
                onclick="htmx.ajax('GET', '{self.search_url}?status=paused',
                    {{target: '#{self.view_id}', swap: 'outerHTML'}});"
                """,
            ),
        ]
        self.actions = [
            {
                "action": _("Edit"),
                "icon": "create-outline",
                "attrs": """
                    class="oh-btn oh-btn--light-bkg oh-btn--sq-sm"
                    title="{% trans 'Edit' %}"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    hx-get="{get_edit_url}"
                    hx-target="#genericModalBody"
                """,
            },
            {
                "action": _("Send now"),
                "icon": "send-outline",
                "attrs": """
                    class="oh-btn oh-btn--success oh-btn--sq-sm"
                    title="{% trans 'Send now' %}"
                    hx-confirm="{% trans 'Send this report now?' %}"
                    hx-post="{get_run_url}"
                    hx-target="#relatedModel"
                """,
            },
            {
                "action": _("Pause/Activate"),
                "icon": "power-outline",
                "attrs": """
                    class="oh-btn oh-btn--light-bkg oh-btn--sq-sm"
                    title="{% trans 'Pause or activate' %}"
                    hx-post="{get_toggle_url}"
                    hx-target="#relatedModel"
                """,
            },
            {
                "action": _("Delete"),
                "icon": "trash-outline",
                "attrs": """
                    class="oh-btn oh-btn--danger oh-btn--sq-sm"
                    title="{% trans 'Delete' %}"
                    hx-confirm="{% trans 'Delete this subscription?' %}"
                    hx-post="{get_delete_url}"
                    hx-target="#relatedModel"
                """,
            },
        ]

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        # HorillaListView's base get_queryset() ultimately calls the manager's
        # .all(), which auto-hides is_active=False rows (HorillaCompanyManager
        # convention). A paused subscription is a real, user-toggleable state
        # here, not a soft-delete — it must stay visible so the owner can
        # re-activate it. Seed from .get_queryset() (company-scoped only, no
        # is_active filtering) instead of letting super() pull in .all().
        if queryset is None:
            queryset = ReportSubscription.objects.get_queryset()
        queryset = super().get_queryset(queryset, filtered, *args, **kwargs)
        queryset = queryset.filter(owner=self.request.user).select_related("company_id")
        status = self.request.GET.get("status")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "paused":
            queryset = queryset.filter(is_active=False)
        return queryset


@method_decorator(login_required, name="dispatch")
class ReportSubscriptionFormView(HorillaFormView):
    """
    Real Horilla create/edit form component (base.forms.ModelForm +
    generic/form.html) — one view handles all three entry points:
      - locked create: URL supplies `slug` (a report row's Subscribe icon)
      - picker create: URL supplies neither `slug` nor `pk` (the
        Subscriptions list's own Create button — no report context yet)
      - edit: URL supplies `pk` (a subscription row's Edit action)
    """

    model = ReportSubscription
    form_class = ReportSubscriptionForm
    new_display_title = _("Create a subscription")

    def _permission_denied(self, request: HttpRequest) -> HttpResponse:
        message = _("You do not have permission to subscribe to this report.")
        messages.error(request, message)
        return HttpResponseForbidden(message)

    def get(self, request: HttpRequest, *args: Any, pk=None, slug=None, **kwargs: Any):
        if slug and not pk:
            definition = get_report(slug)
            company_id = company_id_from_request(request)
            if not definition or not user_can_subscribe_report(
                request.user, definition, company_id=company_id
            ):
                return self._permission_denied(request)
        return super().get(request, *args, pk=pk, slug=slug, **kwargs)

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return ReportSubscription.objects.filter(pk=pk, owner=self.request.user).first()

    def get_initial(self):
        initial = super().get_initial()
        slug = self.kwargs.get("slug")
        creating = not self.kwargs.get("pk")
        if creating:
            if slug:
                initial["report_slug"] = slug
                definition = get_report(slug)
                if definition:
                    initial.setdefault("name", str(definition.name))
            initial.setdefault("frequency", "weekly")
            initial.setdefault("format", "xlsx")
            initial.setdefault(
                "recipients", getattr(self.request.user, "email", "") or ""
            )
        return initial

    def init_form(self, *args, data={}, files={}, instance=None, **kwargs):
        lock_report = self.kwargs.get("slug") if not self.kwargs.get("pk") else None
        report_choices = None
        if not instance and not lock_report:
            company_id = company_id_from_request(self.request)
            grouped = reports_by_domain(user=self.request.user, company_id=company_id)
            report_choices = []
            for domain, reports in grouped.items():
                label = str(DOMAIN_LABELS.get(domain, domain))
                for r in reports:
                    if user_can_subscribe_report(
                        self.request.user, r, company_id=company_id
                    ):
                        report_choices.append((r.slug, f"{label} — {r.name}"))
        return self.form_class(
            data,
            files,
            instance=instance,
            initial=self.get_initial(),
            lock_report=lock_report,
            report_choices=report_choices,
        )

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Edit %(name)s") % {
                "name": self.form.instance.name
            }
        return context

    def form_invalid(self, form: ReportSubscriptionForm) -> HttpResponse:
        if not form.is_valid():
            if form.instance.pk:
                self.form_class.verbose_name = _("Edit %(name)s") % {
                    "name": form.instance.name
                }
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: ReportSubscriptionForm) -> HttpResponse:
        slug = form.cleaned_data.get("report_slug") or self.kwargs.get("slug")
        definition = get_report(slug)
        company_id = company_id_from_request(self.request)
        if not definition or not user_can_subscribe_report(
            self.request.user, definition, company_id=company_id
        ):
            return self._permission_denied(self.request)

        creating = not form.instance.pk
        form.save()
        messages.success(
            self.request,
            _("Subscription created.") if creating else _("Subscription updated."),
        )
        return self.HttpResponse()


@method_decorator(login_required, name="dispatch")
class ReportSubscriptionDetailView(HorillaDetailedView):
    """Real Horilla detailed-view component — opened by clicking a row on
    the Subscriptions list. No avatar/header card (subscriptions have no
    visual identity beyond their name), so header is disabled and the name
    is used as the modal title instead."""

    model = ReportSubscription
    pk_url_kwarg = "subscription_id"
    header = False
    body = [
        (_("Report"), "report_name"),
        (_("Frequency"), "frequency_label"),
        (_("Attachment"), "format_label"),
        (_("Recipients"), "recipients"),
        (_("Status"), "status_label"),
        (_("Last sent"), "last_run_at"),
        (_("Created"), "created_at"),
    ]

    def get_queryset(self):
        return ReportSubscription.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        if context.get("object"):
            context["title"] = context["object"].name
        return context
