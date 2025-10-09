"""
this page handles cbv of key result page
"""

import json
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from base.methods import closest_numbers
from horilla.decorators import manager_can_enter
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.history import HorillaHistoryView
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from pms.filters import ActualKeyResultFilter
from pms.forms import KRForm
from pms.models import EmployeeKeyResult, KeyResult


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultViewPage(TemplateView):
    """
    for key result page
    """

    template_name = "cbv/key_results/key_result_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultNavView(HorillaNavView):
    """
    navbar of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("filter-key-result")

        self.create_attrs = f"""
                        data-toggle="oh-modal-toggle"
                        data-target="#genericModal"
                        hx-get="{reverse('create-key-result')}"
                        hx-target="#genericModalBody"
                        """

        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("filter-key-result"),
                "attrs": """
                            title='List'
                            """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("key-result-card-view"),
                "attrs": """
                            title='Card'
                            """,
            },
        ]

    nav_title = _("Key Results")
    filter_instance = ActualKeyResultFilter()
    filter_body_template = "cbv/key_results/key_result_filter.html"
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultsListView(HorillaListView):

    model = KeyResult
    filter_class = ActualKeyResultFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("filter-key-result")
        self.view_id = "key-result-container"

    columns = [
        (_("Key Results"), "title"),
        (_("Progress Type"), "get_progress_type"),
        (_("Target Value"), "target_value"),
        (_("Duration"), "duration"),
        (_("Description"), "description"),
    ]

    sortby_mapping = [
        ("Progress Type", "get_progress_type"),
        ("Target Value", "target_value"),
        ("Duration", "duration"),
    ]

    header_attrs = {
        "description": 'style="width: 300px;"',
    }

    action_method = "action_col"

    row_attrs = """
                hx-get='{get_detail_url}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        active = (
            True
            if self.request.GET.get("is_active", True)
            in ["unknown", "True", "true", True]
            else False
        )
        queryset = queryset.filter(is_active=active)
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultCardView(HorillaCardView):
    """
    card view of the page
    """

    model = KeyResult
    filter_class = ActualKeyResultFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("key-result-card-view")
        self.view_id = "key-result-container"

    # def get_context_data(self, **kwargs):
    #     context =  super().get_context_data(**kwargs)
    #     self.request.card_div = "card_div"
    #     return context

    details = {
        "image_src": "get_avatar",
        "title": "{title}",
        "subtitle": "Target Value : {target_value} {progress_type} <br> Duration : {duration} Days",
    }

    card_attrs = """
                hx-get='{get_detail_url}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    actions = [
        {
            "action": _("Edit"),
            "attrs": """
                    class="oh-dropdown__link"
                    hx-get='{get_update_url}?instance_ids={ordered_ids}'
			        hx-target="#genericModalBody"
			        data-toggle="oh-modal-toggle"
			        data-target="#genericModal"
            """,
        },
        {
            "action": _("Delete"),
            "attrs": """
                    class="oh-dropdown__link"
                    hx-confirm="Do you want to delete this Key result?"
                    hx-post='{get_delete_url}'
                    hx-swap="innerHTML"
                    hx-target="#key-result-container"
                """,
        },
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultsDetailedView(HorillaDetailedView):
    """
    Detail View
    """

    model = KeyResult
    title = _("Details")

    header = {
        "title": "title",
        "subtitle": "",
        "avatar": "get_avatar",
    }

    body = [
        (_("Key Results"), "title"),
        (_("Progress Type"), "get_progress_type"),
        (_("Target Value"), "target_value"),
        (_("Duration"), "duration"),
        (_("Description"), "description"),
    ]

    cols = {
        "description": 12,
    }

    action_method = "detail_action_col"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter(perm="pms.view_keyresult"), name="dispatch")
class KeyResultFormView(HorillaFormView):
    """
    form view for create and update key results
    """

    model = KeyResult
    form_class = KRForm
    new_display_title = _("Create Key result")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Key result")

        context["form"] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Key result")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: KRForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(
                    self.request,
                    _(f"Key result {self.form.instance} updated successfully"),
                )
            else:
                messages.success(
                    self.request,
                    _(f"Key result {self.form.instance} created successfully"),
                )
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="employee.delete_actiontype"), name="dispatch"
)
class DeleteKeyResults(View):
    """
    Handle deletion of key results.
    """

    def post(self, request, key_id):
        """
        Handle POST request to delete an action type.
        """

        instances_ids = request.GET.get("instances_ids")
        next_instance = None
        instances_list = None
        if instances_ids:
            instances_list = json.loads(instances_ids)
            previous_instance, next_instance = closest_numbers(instances_list, key_id)
            instances_list.remove(key_id)
        key_result = KeyResult.objects.get(id=key_id)
        if key_result:
            key_result.delete()
            messages.success(request, _("Ket result  deleted successfully!"))

        else:
            messages.error(request, _("Key result not found"))
        paths = {
            "genericModalBody": f"/pms/key-result-detail-view/{next_instance}?instance_ids={instances_list}&deleted=true",
        }
        http_hx_target = self.request.META.get("HTTP_HX_TARGET")
        redirected_path = paths.get(http_hx_target)
        return redirect(redirected_path)


@method_decorator(login_required, name="dispatch")
class EKRHistory(HorillaHistoryView):
    """
    EKR History
    """

    model = EmployeeKeyResult

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.has_perm_to_revert = self.request.user.has_perm(
            "pms.change_employeekeyresult"
        )
