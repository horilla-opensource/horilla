"""
This page is handled the cbv of my leave request page
"""

import contextlib
from datetime import datetime
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import resolve, reverse, reverse_lazy
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
from leave.filters import UserLeaveRequestFilter
from leave.forms import UserLeaveRequestCreationForm
from leave.methods import (
    calculate_requested_days,
    company_leave_dates_list,
    holiday_dates_list,
)
from leave.models import (
    AvailableLeave,
    CompanyLeave,
    Holiday,
    LeaveRequest,
    LeaveType,
    leave_requested_dates,
)
from leave.threading import LeaveMailSendThread
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
class MyLeaveRequestView(TemplateView):
    """
    for my leave request page view
    """

    template_name = "cbv/my_leave_request/my_leave_request_home.html"

    def get_context_data(self, **kwargs: Any):
        """
        context data
        """
        context = super().get_context_data(**kwargs)
        user_leave = AvailableLeave.objects.filter(
            employee_id=self.request.user.employee_get
        )
        context["user_leaves"] = user_leave
        return context


@method_decorator(login_required, name="dispatch")
class MainParentListView(HorillaListView):
    """
    main parent class for list view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("user-request-filter")

    filter_class = UserLeaveRequestFilter
    model = LeaveRequest
    records_per_page = 10
    view_id = "deleteleavedata"
    columns = [
        ("Leave Type", "leave_type_custom"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Requested Days", "requested_days"),
        ("Status", "custom_status_col"),
        ("Comment", "comment_action"),
    ]
    option_method = "cancel_confirmation_action"
    action_method = "leave_actions"
    sortby_mapping = [
        ("Leave Type", "leave_type_id__name", "leave_type_id__get_avatar"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Requested Days", "requested_days"),
        ("Status", "status"),
    ]
    row_status_indications = [
        (
            "rejected--dot",
            _("Rejected"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('rejected');
            $('[name=canceled]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "cancelled--dot",
            _("Cancelled"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('cancelled');
            $('[name=rejected]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "approved--dot",
            _("Approved"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('approved');
            $('[name=rejected]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "requested--dot",
            _("Requested"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('requested');
            $('[name=rejected]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
    ]
    row_status_class = "status-{status}"
    row_attrs = """
                {is_rejected},
                hx-get='{my_leave_request_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
class MyLeaveRequestListView(MainParentListView):
    """
    List view of the page
    """

    def get_queryset(self):
        """
        to filter data
        """
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(employee_id=employee)
        return queryset


class MyLeaveRequestNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("user-request-filter")
        self.filter_instance = UserLeaveRequestFilter()

        self.actions = [
            {
                "action": "Delete",
                "attrs": """
                    class="delete"
                    onclick="
                    myLeaveRequestBulkDelete();
                    "
                    data-action ="delete"
                    style="cursor: pointer; color:red !important"
                """,
            }
        ]

        self.create_attrs = f"""
             hx-get="{reverse_lazy("leave-request-create")}"
             hx-target="#genericModalBody"
             data-target="#genericModal"
             data-toggle="oh-modal-toggle"
         """

    nav_title = _("My Leave requests")
    filter_body_template = "cbv/my_leave_request/filter.html"

    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("leave_type_id", "Leave Type"),
        ("status", "Status"),
        ("requested_days", "Requested Days"),
    ]


class MyLeaveRequestDetailView(HorillaDetailedView):
    """
    detail view of page
    """

    model = LeaveRequest
    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "my_leave_request_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    cols = {"rejected_action": 12, "description": 12}
    body = [
        ("Leave Type", "leave_type_id"),
        ("Days", "requested_days"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Status", "get_status_display"),
        ("Description", "description"),
        ("Reason for Rejection", "rejected_action", True),
        ("View attachment", "attachment_action", True),
    ]
    action_method = "detail_leave_actions"


class MyLeaveRequestForm(HorillaFormView):
    """
    form view
    """

    form_class = UserLeaveRequestCreationForm
    model = LeaveRequest
    template_name = "cbv/my_leave_request/form/inherit.html"

    new_display_title = _("Create Request")

    # def get_initial(self) -> dict:
    #     initial = super().get_initial()
    #     emp = self.request.user.employee_get
    #     initial["employee_id"] = emp
    #     return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.my_leave_request = "my_leave_request"
        emp = self.request.user.employee_get
        available_leaves = emp.available_leave.all()
        assigned_leave_types = LeaveType.objects.filter(
            id__in=available_leaves.values_list("leave_type_id", flat=True)
        )
        self.form.fields["leave_type_id"].queryset = assigned_leave_types
        self.form.fields["employee_id"].initial = emp

        if self.form.instance.pk:
            leave_request = LeaveRequest.objects.get(id=self.form.instance.pk)
            if (
                self.request.user.employee_get == leave_request.employee_id
                and leave_request.status != "approved"
            ):
                self.form_class(
                    employee=leave_request.employee_id, instance=leave_request
                )
            self.form_class.verbose_name = _("Leave Request Update")

        context["form"] = self.form
        context["view_id"] = "myleaverequest"

        return context

    # def form_invalid(self, form: Any) -> HttpResponse:

    #     form = self.form_class(self.request.POST)
    #     if not form.is_valid():
    #         errors = form.errors.as_data()
    #         return render(
    #             self.request, self.template_name, {"form": form, "errors": errors}
    #         )
    #     return super().form_invalid(form)

    def form_valid(self, form: UserLeaveRequestCreationForm) -> HttpResponse:
        emp = self.request.user.employee_get
        emp_id = emp.id
        form = self.form_class(
            self.request.POST, instance=self.form.instance, employee=emp
        )
        if form.is_valid():
            self.form_class(
                self.request.POST, self.request.FILES, instance=self.form.instance
            )
            if form.instance.pk:
                leave_request = form.save(commit=False)

                start_date = leave_request.start_date
                end_date = leave_request.end_date
                start_date_breakdown = leave_request.start_date_breakdown
                end_date_breakdown = leave_request.end_date_breakdown
                leave_type = leave_request.leave_type_id
                employee = self.request.user.employee_get
                available_leave = AvailableLeave.objects.get(
                    employee_id=employee, leave_type_id=leave_type
                )
                available_total_leave = (
                    available_leave.available_days + available_leave.carryforward_days
                )
                requested_days = calculate_requested_days(
                    start_date, end_date, start_date_breakdown, end_date_breakdown
                )
                requested_dates = leave_requested_dates(start_date, end_date)
                holidays = Holiday.objects.all()
                holiday_dates = holiday_dates_list(holidays)
                company_leaves = CompanyLeave.objects.all()
                company_leave_dates = company_leave_dates_list(
                    company_leaves, start_date
                )
                if (
                    leave_type.exclude_company_leave == "yes"
                    and leave_type.exclude_holiday == "yes"
                ):
                    total_leaves = list(set(holiday_dates + company_leave_dates))
                    total_leave_count = sum(
                        requested_date in total_leaves
                        for requested_date in requested_dates
                    )
                    requested_days = requested_days - total_leave_count
                else:
                    holiday_count = 0
                    if leave_type.exclude_holiday == "yes":
                        for requested_date in requested_dates:
                            if requested_date in holiday_dates:
                                holiday_count += 1
                        requested_days = requested_days - holiday_count
                    if leave_type.exclude_company_leave == "yes":
                        company_leave_count = sum(
                            requested_date in company_leave_dates
                            for requested_date in requested_dates
                        )
                        requested_days = requested_days - company_leave_count
                if requested_days <= available_total_leave:
                    leave_request.save()
                    messages.success(
                        self.request, _("Leave request updated successfully")
                    )
                else:
                    form.add_error(
                        None,
                        _("You dont have enough leave days to make the request"),
                    )
            else:
                if int(form.data["employee_id"]) == int(emp_id):
                    if form.is_valid():
                        # if form.instance.pk:
                        leave_request = form.save(commit=False)
                        save = True
                        if leave_request.leave_type_id.require_approval == "no":
                            employee_id = leave_request.employee_id
                            leave_type_id = leave_request.leave_type_id
                            available_leave = AvailableLeave.objects.get(
                                leave_type_id=leave_type_id, employee_id=employee_id
                            )
                            if (
                                leave_request.requested_days
                                > available_leave.available_days
                            ):
                                leave = (
                                    leave_request.requested_days
                                    - available_leave.available_days
                                )
                                leave_request.approved_available_days = (
                                    available_leave.available_days
                                )
                                available_leave.available_days = 0
                                available_leave.carryforward_days = (
                                    available_leave.carryforward_days - leave
                                )
                                leave_request.approved_carryforward_days = leave
                            else:
                                available_leave.available_days = (
                                    available_leave.available_days
                                    - leave_request.requested_days
                                )
                                leave_request.approved_available_days = (
                                    leave_request.requested_days
                                )
                            leave_request.status = "approved"
                            available_leave.save()
                        if save:
                            leave_request.created_by = self.request.user.employee_get
                            leave_request.save()
                            messages.success(
                                self.request,
                                _("Leave request created successfully"),
                            )
                            with contextlib.suppress(Exception):
                                notify.send(
                                    self.request.user.employee_get,
                                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                                    verb=f"New leave request created for {leave_request.employee_id}.",
                                    verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                                    verb_de=f"Neuer Urlaubsantrag für {leave_request.employee_id} erstellt.",
                                    verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                                    verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                                    icon="people-circle",
                                    redirect=reverse("request-view")
                                    + f"?id={leave_request.id}",
                                )
                            mail_thread = LeaveMailSendThread(
                                self.request, leave_request, type="request"
                            )
                            mail_thread.start()
                            form = UserLeaveRequestCreationForm(employee=emp)
                            if (
                                len(LeaveRequest.objects.filter(employee_id=emp_id))
                                == 1
                            ):
                                return HttpResponse(
                                    "<script>window.location.reload();</script>"
                                )
                            form.save(commit=False)

                        return HttpResponse("<script>location.reload();</script>")
                else:
                    messages.error(self.request, _("You don't have permission"))

            return HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class MyLeaveRequestSingleForm(HorillaFormView):
    """
    single leave request form
    """

    model = LeaveRequest
    form_class = UserLeaveRequestCreationForm
    new_display_title = _("Leave Request")
    template_name = "cbv/my_leave_request/form/inherit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_get
        resolved = resolve(self.request.path_info)
        leave_id = resolved.kwargs.get("leave")
        leave_type = LeaveType.objects.filter(id=leave_id)
        form = self.form_class(
            initial={"employee_id": employee, "leave_type_id": leave_type.first()}
        )

        self.form_class.verbose_name = _("Leave Request")
        form.fields["leave_type_id"].queryset = leave_type

        context["form"] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        form = self.form_class(self.request.POST)
        self.form_class.verbose_name = _("Leave Request")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: UserLeaveRequestCreationForm) -> HttpResponse:
        employee = self.request.user.employee_get
        resolved = resolve(self.request.path_info)
        leave_id = resolved.kwargs.get("leave")
        leave_type = LeaveType.objects.get(id=leave_id)
        form = self.form_class(self.request.POST, self.request.FILES, employee=employee)
        start_date = datetime.strptime(self.request.POST.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(self.request.POST.get("end_date"), "%Y-%m-%d")
        start_date_breakdown = self.request.POST.get("start_date_breakdown")
        end_date_breakdown = self.request.POST.get("end_date_breakdown")
        available_leave = AvailableLeave.objects.get(
            employee_id=employee, leave_type_id=leave_type
        )
        available_total_leave = (
            available_leave.available_days + available_leave.carryforward_days
        )
        requested_days = calculate_requested_days(
            start_date, end_date, start_date_breakdown, end_date_breakdown
        )
        requested_dates = leave_requested_dates(start_date, end_date)
        requested_dates = [date.date() for date in requested_dates]
        holidays = Holiday.objects.all()
        holiday_dates = holiday_dates_list(holidays)
        company_leaves = CompanyLeave.objects.all()
        company_leave_dates = company_leave_dates_list(company_leaves, start_date)
        if (
            leave_type.exclude_company_leave == "yes"
            and leave_type.exclude_holiday == "yes"
        ):
            total_leaves = list(set(holiday_dates + company_leave_dates))
            total_leave_count = sum(
                requested_date in total_leaves for requested_date in requested_dates
            )
            requested_days = requested_days - total_leave_count
        else:
            holiday_count = 0
            if leave_type.exclude_holiday == "yes":
                for requested_date in requested_dates:
                    if requested_date in holiday_dates:
                        holiday_count += 1
                requested_days = requested_days - holiday_count
            if leave_type.exclude_company_leave == "yes":
                company_leave_count = sum(
                    requested_date in company_leave_dates
                    for requested_date in requested_dates
                )
                requested_days = requested_days - company_leave_count
        overlapping_requests = LeaveRequest.objects.filter(
            employee_id=employee, start_date__lte=end_date, end_date__gte=start_date
        ).exclude(status__in=["cancelled", "rejected"])
        if overlapping_requests.exists():
            form.add_error(
                None, _("There is already a leave request for this date range")
            )
        elif requested_days <= available_total_leave or form.instance.status not in [
            "approved"
        ]:
            if form.is_valid():
                leave_request = form.save(commit=False)
                save = True
                leave_request.leave_type_id = leave_type
                leave_request.employee_id = employee

                if leave_request.leave_type_id.require_approval == "no":
                    employee_id = leave_request.employee_id
                    leave_type_id = leave_request.leave_type_id
                    available_leave = AvailableLeave.objects.get(
                        leave_type_id=leave_type_id, employee_id=employee_id
                    )
                    if leave_request.requested_days > available_leave.available_days:
                        leave = (
                            leave_request.requested_days
                            - available_leave.available_days
                        )
                        leave_request.approved_available_days = (
                            available_leave.available_days
                        )
                        available_leave.available_days = 0
                        available_leave.carryforward_days = (
                            available_leave.carryforward_days - leave
                        )
                        leave_request.approved_carryforward_days = leave
                    else:
                        available_leave.available_days = (
                            available_leave.available_days
                            - leave_request.requested_days
                        )
                        leave_request.approved_available_days = (
                            leave_request.requested_days
                        )
                    leave_request.status = "approved"
                    available_leave.save()
                if save:
                    leave_request.created_by = employee
                    leave_request.save()
                    messages.success(
                        self.request, _("Leave request created successfully")
                    )
                    with contextlib.suppress(Exception):
                        notify.send(
                            self.request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb="You have a new leave request to validate.",
                            verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                            verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                            verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                            verb_fr="Vous avez une nouvelle demande de congé à valider.",
                            icon="people-circle",
                            redirect=reverse("request-view")
                            + f"?id={leave_request.id}",
                        )
                        return HttpResponse("<script>window.location.reload()</script>")
                    if len(
                        LeaveRequest.objects.filter(employee_id=employee)
                    ) == 1 or self.request.META.get("HTTP_REFERER").endswith(
                        "employee-profile/"
                    ):
                        return HttpResponse("<script>window.location.reload()</script>")
                else:
                    form.add_error(
                        None,
                        _("You dont have enough leave days to make the request"),
                    )

                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return self.form_invalid(form)
        return super().form_valid(form)
