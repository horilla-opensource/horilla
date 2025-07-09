"""
horilla_automations/views/cbvs.py
"""

import json
import os

from django.conf import settings
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _trans
from django.views import View

from base.models import HorillaMailTemplate
from horilla.decorators import login_required, permission_required
from horilla_automations import models
from horilla_automations.filters import AutomationFilter
from horilla_automations.forms import AutomationForm
from horilla_views.generic.cbv import views


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.view_mailautomation"), name="dispatch"
)
class AutomationSectionView(views.HorillaSectionView):
    """
    AutomationSectionView
    """

    nav_url = reverse_lazy("mail-automations-nav")
    view_url = reverse_lazy("mail-automations-list-view")
    view_container_id = "listContainer"

    script_static_paths = [
        "/automation/automation.js",
    ]

    template_name = "horilla_automations/section_view.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.view_mailautomation"), name="dispatch"
)
class AutomationNavView(views.HorillaNavView):
    """
    AutomationNavView
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.actions = []
        if self.request.user.has_perm("horilla_automations.add_mailautomation"):
            self.create_attrs = f"""
                hx-get="{reverse_lazy("create-automation")}"
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
            """

            self.actions.append(
                {
                    "action": "Load Automations",
                    "attrs": f"""
                        data-toggle="oh-modal-toggle"
                        data-target="#genericModal"
                        hx-target="#genericModalBody"
                        hx-get="{reverse_lazy('load-automations')}"
                        style="cursor: pointer;"
                    """,
                }
            )

        if self.request.user.has_perm("horilla_automations.add_mailautomation"):
            self.actions.append(
                {
                    "action": "Refresh Automations",
                    "attrs": f"""
                        hx-get="{reverse_lazy('refresh-automations')}"
                        hx-target="#reloadMessages"
                        class="oh-btn oh-btn--light-bkg"
                    """,
                }
            )

    nav_title = _trans("Automations")
    search_url = reverse_lazy("mail-automations-list-view")
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.change_mailautomation"), name="dispatch"
)
class AutomationFormView(views.HorillaFormView):
    """
    AutomationFormView
    """

    form_class = AutomationForm
    model = models.MailAutomation
    new_display_title = _trans("New Automation")
    template_name = "horilla_automations/automation_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = models.MailAutomation.objects.filter(pk=self.kwargs["pk"]).first()
        kwargs["instance"] = instance

        return kwargs

    def form_valid(self, form: AutomationForm) -> views.HttpResponse:
        if form.is_valid():
            message = "New automation added"
            if form.instance.pk:
                message = "Automation updated"
            form.save()

            messages.success(self.request, _trans(message))
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.view_mailautomation"), name="dispatch"
)
class AutomationListView(views.HorillaListView):
    """
    AutomationListView
    """

    row_attrs = """
            hx-get="{detailed_url}?instance_ids={ordered_ids}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
        """

    model = models.MailAutomation
    search_url = reverse_lazy("mail-automations-list-view")
    filter_class = AutomationFilter

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-100"
                hx-get="{edit_url}?instance_ids={ordered_ids}"
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
            """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
            class="oh-btn oh-btn--light-bkg w-100 tex-danger"
            onclick="
                event.stopPropagation();
                confirm('Do you want to delete the automation?','{delete_url}')
            "
            """,
        },
    ]
    header_attrs = {"action": "style='width:100px;'"}
    columns = [
        ("Title", "title"),
        ("Model", "model"),
        ("Trigger", "trigger_display"),
        ("Delivery Channel", "get_delivery_channel_display"),
        ("Email Mapping", "get_mail_to_display"),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.view_mailautomation"), name="dispatch"
)
class AutomationDetailedView(views.HorillaDetailedView):
    """
    AutomationDetailedView
    """

    model = models.MailAutomation
    title = "Detailed View"
    header = {
        "title": "title",
        "subtitle": "title",
        "avatar": "get_avatar",
    }
    body = [
        ("Model", "model"),
        ("Mail Templates", "mail_template"),
        ("Mail To", "get_mail_to_display"),
        ("Mail Cc", "get_mail_cc_display"),
        ("Trigger", "trigger_display"),
    ]
    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
            hx-get="{edit_url}?instance_ids={ordered_ids}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            class="oh-btn oh-btn--info w-50"
            """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
            class="oh-btn oh-btn--danger w-50"
            onclick="
                confirm('Do you want to delete the automation?','{delete_url}')
            "
            """,
        },
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_automations.add_mailautomation"), name="dispatch"
)
class LoadAutomationsView(View):
    template_name = "horilla_automations/load_automation.html"
    template_file = os.path.join(settings.BASE_DIR, "load_data", "mail_templates.json")
    automation_file = os.path.join(
        settings.BASE_DIR, "load_data", "mail_automations.json"
    )

    def load_json_files(self):
        with open(self.template_file, "r") as tf:
            templates_raw = json.load(tf)
        with open(self.automation_file, "r") as af:
            automations_raw = json.load(af)
        return templates_raw, automations_raw

    def get(self, request):
        templates_raw, automations_raw = self.load_json_files()

        template_lookup = {item["pk"]: item["fields"]["body"] for item in templates_raw}

        processed_automations = []
        for automation in automations_raw:
            processed = automation.copy()
            template_pk = automation["fields"].get("mail_template")
            processed["template_body"] = template_lookup.get(template_pk, "")
            processed_automations.append(processed)

        return render(
            request,
            self.template_name,
            {"automations": processed_automations},
        )

    def post(self, request):
        templates_raw, automations_raw = self.load_json_files()

        template_lookup = {item["pk"]: item["fields"]["body"] for item in templates_raw}

        selected_ids = [int(k) for k in request.POST.keys() if k.isdigit()]
        selected_automations = [a for a in automations_raw if a["pk"] in selected_ids]

        required_template_pks = {
            a["fields"].get("mail_template")
            for a in selected_automations
            if a["fields"].get("mail_template")
        }

        for template_json in templates_raw:
            if template_json["pk"] in required_template_pks:
                template_data = list(
                    serializers.deserialize("json", json.dumps([template_json]))
                )[0].object
                existing = HorillaMailTemplate.objects.filter(
                    title=template_data.title
                ).first()
                if not existing:
                    template_data.pk = None
                    template_data.save()

        for automation_json in selected_automations:
            deserialized = list(
                serializers.deserialize("json", json.dumps([automation_json]))
            )[0]
            automation_obj = deserialized.object

            template_pk = automation_json["fields"].get("mail_template")
            template_body = template_lookup.get(template_pk)
            mail_template = HorillaMailTemplate.objects.filter(
                body=template_body
            ).first()
            automation_obj.mail_template = mail_template

            if not models.MailAutomation.objects.filter(
                title=automation_obj.title
            ).exists():
                automation_obj.pk = None
                automation_obj.save()

                messages.success(
                    request, f"Automation '{automation_obj.title}' added successfully."
                )
            else:
                messages.warning(
                    request, f"Automation '{automation_obj.title}' already exists."
                )

        script = """
            <script>
                $("#reloadMessagesButton").click();
                $('#applyFilter').click();
                $('.oh-modal--show').first().removeClass('oh-modal--show');
            </script>
        """
        return HttpResponse(script)
