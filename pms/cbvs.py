from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _trans

from base.methods import filter_own_and_subordinate_recordes, is_reportingmanager
from horilla import horilla_middlewares
from horilla.decorators import login_required, permission_required
from horilla_views.generic.cbv import views
from pms import models
from pms.filters import BonusPointSettingFilter, EmployeeBonusPointFilter
from pms.forms import BonusPointSettingForm, EmployeeBonusPointForm


# ================Models for BonusPointSetting==============
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("pms.view_bonuspointsetting"), name="dispatch")
class BonusPointSettingSectionView(views.HorillaSectionView):
    """
    BonusPointSetting SectionView
    """

    nav_url = reverse_lazy("bonus-point-setting-nav")
    view_url = reverse_lazy("bonus-point-setting-list-view")
    view_container_id = "listContainer"

    # script_static_paths = [
    #     "static/automation/automation.js",
    # ]

    template_name = "bonus/bonus_point_setting_section.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("pms.view_bonuspointsetting"), name="dispatch")
class BonusPointSettingNavView(views.HorillaNavView):
    """
    BonusPointSetting nav view
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.create_attrs = f"""
            hx-get="{reverse_lazy("create-bonus-point-setting")}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
        """

    nav_title = _trans("Bonus Point Setting")
    search_url = reverse_lazy("bonus-point-setting-list-view")
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("pms.change_bonuspointsetting"), name="dispatch")
class BonusPointSettingFormView(views.HorillaFormView):
    """
    BonusPointSettingForm View
    """

    form_class = BonusPointSettingForm
    model = models.BonusPointSetting
    new_display_title = _trans("Create Bonus Point Setting")
    template_name = "bonus/bonus_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = models.BonusPointSetting.objects.filter(pk=self.kwargs["pk"]).first()
        kwargs["instance"] = instance
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: BonusPointSettingForm) -> views.HttpResponse:
        if form.is_valid():
            message = "Bonus Point Setting added"
            if form.instance.pk:
                message = "Bonus Point Setting updated"
            form.save()

            messages.success(self.request, _trans(message))
            return self.HttpResponse()

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("pms.view_bonuspointsetting"), name="dispatch")
class BonusPointSettingListView(views.HorillaListView):
    """
    BnusPointSetting list view
    """

    model = models.BonusPointSetting
    search_url = reverse_lazy("bonus-point-setting-list-view")
    filter_class = BonusPointSettingFilter
    action_method = "action_template"

    columns = [
        ("Model", "get_model_display"),
        ("Applicable For", "get_applicable_for_display"),
        ("Bonus For", "get_bonus_for_display"),
        ("Condition", "get_condition"),
        ("Points", "points"),
        ("Is Active", "is_active_toggle"),
    ]


# ================Models for EmployeeBonusPoint==============


class EmployeeBonusPointSectionView(views.HorillaSectionView):
    """
    EmployeeBonusPoint SectionView
    """

    nav_url = reverse_lazy("employee-bonus-point-nav")
    view_url = reverse_lazy("employee-bonus-point-list-view")
    view_container_id = "listContainer"

    # script_static_paths = [
    #     "static/automation/automation.js",
    # ]

    template_name = "bonus/employee_bonus_point_section.html"


class EmployeeBonusPointNavView(views.HorillaNavView):
    """
    BonusPoint nav view
    """

    template_name = "bonus/bonus_point_nav.html"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        request = self.request
        if request:
            if is_reportingmanager(request) or request.user.has_perm(
                "pms.add_employeebonuspoint"
            ):
                self.create_attrs = f"""
                    hx-get="{reverse_lazy("create-employee-bonus-point")}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """

    nav_title = _trans("Employee Bonus Point ")
    search_url = reverse_lazy("employee-bonus-point-list-view")
    search_swap_target = "#listContainer"
    group_by_fields = [
        ("employee_id", _trans("Employee")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _trans("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _trans("Department")),
        ("employee_id__employee_work_info__job_position_id", _trans("Job Position")),
        (
            "employee_id__employee_work_info__employee_type_id",
            _trans("Employement Type"),
        ),
        ("employee_id__employee_work_info__company_id", _trans("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("pms.change_employeebonuspoint"), name="dispatch")
class EmployeeBonusPointFormView(views.HorillaFormView):
    """
    BonusPointForm View
    """

    form_class = EmployeeBonusPointForm
    model = models.EmployeeBonusPoint
    new_display_title = _trans("Create Employee Bonus Point ")
    # template_name = "bonus/bonus_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: EmployeeBonusPointForm) -> views.HttpResponse:
        if form.is_valid():
            message = "Bonus Point added"
            if form.instance.pk:
                message = "Bonus Point updated"
            form.save()
            messages.success(self.request, _trans(message))
            return self.HttpResponse(
                """
                    <script>
                        $('#bonus-tab-button').click()
                    </script>
                """
            )

        return super().form_valid(form)


class EmployeeBonusPointListView(views.HorillaListView):
    """
    BnusPoint list view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = self.request
        if request:
            if is_reportingmanager(request) or request.user.has_perm(
                "pms.change_employeebonuspoint"
            ):
                self.action_method = "action_template"

    model = models.EmployeeBonusPoint
    search_url = reverse_lazy("employee-bonus-point-list-view")
    filter_class = EmployeeBonusPointFilter
    bulk_update_fields = [
        "employee_id",
        "bonus_point",
        "based_on",
    ]

    columns = [
        ("Employee", "employee_id"),
        ("Bonus Point", "bonus_point"),
        ("Based On", "based_on"),
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        if is_reportingmanager(request) or request.user.has_perm(
            "pms.view_employeebonuspoint"
        ):
            return filter_own_and_subordinate_recordes(
                request, queryset, perm="pms.view_employeebonuspoint"
            )
        else:
            return queryset.filter(employee_id=request.user.employee_get)
