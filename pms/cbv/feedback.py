"""
this page handles cbv of assigned leave page
"""

from typing import Any

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.methods import choosesubordinates, is_reportingmanager
from employee.cbv.employee_profile import EmployeeProfileView
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from notifications.signals import notify
from pms.filters import AnonymousFilter, FeedbackFilter
from pms.forms import AnonymousFeedbackForm, FeedbackForm
from pms.models import AnonymousFeedback, EmployeeKeyResult, Feedback
from pms.views import send_feedback_notifications


@method_decorator(login_required, name="dispatch")
class FeedbackViewPage(TemplateView):
    """
    for 360 feedback page
    """

    template_name = "cbv/360_feedback/feedback_home.html"


@method_decorator(login_required, name="dispatch")
class FeedbackListView(HorillaListView):
    """
    list view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("feedback-list-page")

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        archive_param = self.request.GET.get("archive")

        qs = super().get_queryset(queryset, filtered, *args, **kwargs)

        if archive_param in ["true", "True", "1"]:
            # only archived
            qs = qs.filter(archive=True)
        elif archive_param in ["false", "False", "0", "unknown"]:
            # include False and unknown (NULL)
            qs = qs.filter(Q(archive=False) | Q(archive__isnull=True))

        return qs

    model = Feedback
    filter_class = FeedbackFilter
    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Title"), "review_cycle"),
        (_("Status"), "custom_status_style"),
        (_("Start Date"), "start_date"),
        (_("Due On"), "get_feedback_due_date"),
    ]
    export_fields = [
        (
            _("Answers"),
            "question_answer",
            {
                "question_id__question": "Question",
                "answer": "Answer",
                "answer_by": "Answered By",
            },
        ),
    ]
    action_method = "custom_actions_col"

    header_attrs = {
        "action": """style="width:200px!important;" """,
    }

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name"),
        ("Status", "custom_status_style"),
        ("Title", "review_cycle"),
        ("Start Date", "start_date"),
        ("Due On", "due_days_diff"),
    ]

    row_attrs = """
                onclick="
                event.stopPropagation();
                window.location.href='{get_individual_feedback}'"
                """

    row_status_indications = [
        (
            "at_risk--dot",
            _("At Risk"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('At Risk');
            $('#applyFilter').click();
            "
            """,
        ),
        (
            "not_started--dot",
            _("Not Started"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('Not Started');
            $('#applyFilter').click();
            "
            """,
        ),
        (
            "behind--dot",
            _("Behind"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('Behind');
            $('#applyFilter').click();
            "
            """,
        ),
        (
            "closed--dot",
            _("Closed"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('Closed');
            $('#applyFilter').click();
            "
            """,
        ),
        (
            "on_track--dot",
            _("On Track"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('On Track');
            $('#applyFilter').click();
            "
            """,
        ),
    ]

    row_status_class = "status-{status}"


@method_decorator(login_required, name="dispatch")
class FeedbackGenericTabView(HorillaTabView):
    """
    tab view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("feedback-generic-tab")

        tabs = [
            {
                "title": _("Self Feedback"),
                "url": f"{reverse('self-feedback-tab')}",
            },
            {
                "title": _("Requested Feedback"),
                "url": f"{reverse('requested-feedback-tab')}",
            },
            {
                "title": _("Anonymous Feedback"),
                "url": f"{reverse('anonymous-feedback-tab')}",
                "actions": [
                    {
                        "action": "Add Anonymous",
                        "attrs": f"""
                                data-toggle = "oh-modal-toggle"
                                data-target = "#genericModal"
                                hx-target="#genericModalBody"
                                hx-get ="{reverse('add-anonymous-feedback')}"
                                style="cursor: pointer;"
                            """,
                    }
                ],
            },
        ]
        if self.request.user.has_perm("pms.view_feedback") or is_reportingmanager(
            self.request
        ):
            tabs.insert(
                2,
                {
                    "title": _("Feedbacks to Review"),
                    "url": f"{reverse('all-feedback-tab')}",
                },
            )

        self.tabs = tabs


@method_decorator(login_required, name="dispatch")
class SelfFeedbacktab(FeedbackListView):
    """
    self feedback tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("self-feedback-tab")
        self.request.self_feedback = "self_feedback"

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        # employee = Employee.objects.filter(employee_user_id=user).first()
        queryset = queryset.filter(employee_id=employee).filter(
            employee_id__is_active=True
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class RequestedFeedbackTab(FeedbackListView):
    """
    requested feedback tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("requested-feedback-tab")
        self.request.request_feedback = "request_feedback"
        self.row_attrs = ""

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        # employee = Employee.objects.filter(employee_user_id=user).first()
        feedback_requested_ids = queryset.filter(
            Q(manager_id=employee, manager_id__is_active=True)
            | Q(colleague_id=employee, colleague_id__is_active=True)
            | Q(subordinate_id=employee, subordinate_id__is_active=True)
            | Q(others_id=employee, others_id__is_active=True)
        ).values_list("id", flat=True)

        queryset = queryset.filter(pk__in=feedback_requested_ids).filter(
            employee_id__is_active=True
        )

        return queryset


@method_decorator(login_required, name="dispatch")
class AllFeedbackTab(FeedbackListView):
    """
    all feedback tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("all-feedback-tab")
        self.request.all_feedback = "all_feedback"

    def get_queryset(self):
        queryset = super().get_queryset()
        # employee = self.request.user
        employee = self.request.user.employee_get
        if self.request.user.has_perm("pms.view_feedback"):
            queryset = queryset.filter(employee_id__is_active=True)
        else:
            # employee = self.request.user.employee_get
            if employee:
                data = Employee.objects.filter(
                    employee_work_info__reporting_manager_id=employee, is_active=True
                )
                queryset = queryset.filter(
                    employee_id__in=data, employee_id__is_active=True
                )
        return queryset


@method_decorator(login_required, name="dispatch")
class AnonymousFeedbackTab(HorillaListView):
    """
    anonymous feedback tab
    """

    selected_instances_key_id = "anounyselectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("anonymous-feedback-tab")

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        archive_param = self.request.GET.get("archive")
        qs = super().get_queryset(queryset, filtered, *args, **kwargs)

        if archive_param in ["true", "True", "1"]:
            qs = qs.filter(archive=True)
        elif archive_param in ["false", "False", "0", "unknown"]:
            qs = qs.filter(Q(archive=False) | Q(archive__isnull=True))

        employee = self.request.user.employee_get
        if not self.request.user.has_perm("pms.view_feedback"):
            qs = qs.filter(employee_id=employee)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        querys = self.get_queryset()
        anonymous_feedback_ids = querys.values_list("anonymous_feedback_id", flat=True)
        context["created_user"] = anonymous_feedback_ids
        return context

    model = AnonymousFeedback
    filter_class = AnonymousFilter

    columns = [
        (_("Subject"), "feedback_subject"),
        (_("Based on"), "get_based_on_value"),
        (_("Created At"), "created_at"),
    ]

    header_attrs = {
        "action": """
                    style="width:100px !important;"
                """
    }

    sortby_mapping = [("Created At", "created_at")]

    action_method = "anonymous_actions_col"

    row_attrs = """
                onclick="
                event.stopPropagation();"
                hx-get='{get_individual_anonymous_feedback}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                data-anounymous = "true"

                """


class FeedbacknavView(HorillaNavView):
    """
    navbar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("feedback-generic-tab")
        self.actions = [
            {
                "action": _("Archive"),
                "attrs": """
                    id="archiveFeedback"
                    style="cursor: pointer;"
                """,
            },
            {
                "action": _("Un-Archive"),
                "attrs": """
                    id="UnarchiveFeedback"
                    style="cursor: pointer;"
                """,
            },
        ]
        if self.request.user.has_perm("pms.add_feedback"):
            self.actions.append(
                {
                    "action": _("Bulk feedback"),
                    "attrs": f"""
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get ="{reverse_lazy('bulk-feedback-create')}"
                        hx-target="#objectCreateModalTarget"
                        class="oh-dropdown__link"
                        id="bulkfeedback"
                        style="cursor: pointer;"
                    """,
                }
            )
        if self.request.user.has_perm("pms.view_feedback") or is_reportingmanager(
            self.request
        ):
            self.create_attrs = """
                 href="/pms/feedback-creation"
             """
            self.actions.append(
                {
                    "action": _("Delete"),
                    "attrs": """
                        id="deleteFeedback"
                        data-action ="delete"
                        style="cursor: pointer; color:red !important"
                    """,
                }
            )

    nav_title = _("Feedbacks")
    filter_body_template = "cbv/360_feedback/feedback_filter.html"
    filter_instance = FeedbackFilter()
    filter_form_context_name = "feedback_filter_form"
    search_swap_target = "#listContainer"


class AddAnonymousFeedbackForm(HorillaFormView):
    """
    form view
    """

    form_class = AnonymousFeedbackForm
    model = AnonymousFeedback
    template_name = "cbv/360_feedback/inherit.html"
    new_display_title = _("Anonymous Feedback")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # form = self.form_class(instance=self.form.instance)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Anonymous Feedback")

        context["form"] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Anonymous Feedback")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: AnonymousFeedbackForm) -> HttpResponse:
        anonymous_id = self.request.user.id
        feedback = form.save(commit=False)
        feedback.anonymous_feedback_id = anonymous_id
        form = self.form_class(self.request.POST, instance=feedback)
        if form.is_valid():
            if form.instance.pk:
                message = _("Feedback Updated Successfully")
            else:
                message = _("Feedback Created Successfully")
                if feedback.based_on == "employee":
                    notify.send(
                        User.objects.filter(username="Horilla Bot").first(),
                        recipient=feedback.employee_id.employee_user_id,
                        verb="You received an anonymous feedback!",
                        verb_ar="لقد تلقيت تقييمًا مجهولًا!",
                        verb_de="Sie haben anonymes Feedback erhalten!",
                        verb_es="¡Has recibido un comentario anónimo!",
                        verb_fr="Vous avez reçu un feedback anonyme!",
                        redirect=reverse("feedback-view"),
                        icon="bag-check",
                    )
            feedback.save()
            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)


class PerformanceTab(SelfFeedbacktab):
    """
    performance tab in employee profile
    """

    records_per_page = 2

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("individual-performance-tab-list", kwargs={"pk": pk})

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = Feedback.objects.filter(employee_id=pk, archive=False)
        return queryset


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Performance",
            "view": PerformanceTab.as_view(),
            "accessibility": "pms.cbv.accessibility.performance_accessibility",
        },
    ]
)


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.change_feedback"), name="dispatch")
class FeedbackUpdateFormView(HorillaFormView):
    """
    Form View for update feedback
    """

    form_class = FeedbackForm
    model = Feedback
    template_name = "cbv/360_feedback/form/form_inherit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            employees = self.form.instance.employee_id
            subordinate_ids = self.form.instance.subordinate_id.values_list(
                "id", flat=True
            )
            subordinate_ids_list = list(subordinate_ids)
            key_result = EmployeeKeyResult.objects.filter(
                employee_objective_id__employee_id=employees.id
            )

            self.form_class.verbose_name = _("Update Feedback")
            self.form.fields["employee_key_results_id"].queryset = key_result
            self.form.fields["subordinate_id"].initial = subordinate_ids_list
            context["subordinates"] = subordinate_ids_list
        context["form"] = self.form
        context["feedback_form"] = self.form
        return context

    def form_valid(self, form: FeedbackForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                employees = form.data.getlist("subordinate_id")
                if key_result_ids := self.request.POST.getlist(
                    "employee_key_results_id"
                ):
                    for key_result_id in key_result_ids:
                        key_result = EmployeeKeyResult.objects.filter(
                            id=key_result_id
                        ).first()
                        feedback_form = form.save()
                        feedback_form.employee_key_results_id.add(key_result)
                instance = form.save()
                instance.subordinate_id.set(employees)
                form = form.save()
                message = _("Feedback updated successfully!")
                send_feedback_notifications(self.request, form)
            # form.save()

            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


class AnounyFeedbackDetailView(HorillaDetailedView):

    model = AnonymousFeedback

    title = _("Details")

    header = {"title": "detail_view_subtitle", "subtitle": ""}

    body = [
        (_("Subject"), "feedback_subject"),
        (_("Based On"), "based_on"),
        (_("Description"), "feedback_description"),
    ]

    cols = {
        "feedback_description": 12,
    }
