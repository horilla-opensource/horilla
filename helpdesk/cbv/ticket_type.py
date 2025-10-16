"""
this page is handling the cbv methods for Ticket types in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import Attachment
from employee.models import Employee
from helpdesk.cbv.tags import DynamicTagsCreateFormView
from helpdesk.filter import TicketTypeFilter
from helpdesk.forms import TicketForm, TicketTypeForm
from helpdesk.models import Ticket, TicketType
from helpdesk.threading import TicketSendThread
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.view_tickettype"), name="dispatch")
class TicketsListView(HorillaListView):
    """
    list view for tickets in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("ticket-list")
        self.actions = []
        if self.request.user.has_perm("helpdesk.change_tickettype"):
            self.actions.append(
                {
                    "action": _("Edit"),
                    "icon": "create-outline",
                    "attrs": """
                                class="oh-btn oh-btn--light-bkg w-100"
                                hx-get='{get_update_url}?instance_ids={ordered_ids}'
                                        hx-target="#genericModalBody"
                                        data-toggle="oh-modal-toggle"
                                        data-target="#genericModal"
                            """,
                },
            )
        if self.request.user.has_perm("helpdesk.delete_tickettype"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                        class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                        hx-get="{get_delete_url}?model=helpdesk.tickettype&pk={pk}"
                        data-toggle="oh-modal-toggle"
                        data-target="#deleteConfirmation"
                        hx-target="#deleteConfirmationBody"
                    """,
                },
            )

    model = TicketType
    filter_class = TicketTypeFilter
    show_toggle_form = False

    columns = [
        (_("Ticket Type"), "title"),
        (_("Type"), "get_type_display"),
        (_("Prefix"), "prefix"),
    ]

    header_attrs = {"title": """ style = "width:200px !important" """}

    sortby_mapping = [
        ("Ticket Type", "title"),
        ("Type", "type"),
        ("Prefix", "prefix"),
    ]

    row_attrs = """
                id="ticketTypeTr{get_delete_instance}"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.view_tickettype"), name="dispatch")
class TicketsNavView(HorillaNavView):
    """
    nav bar of the department view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("ticket-list")
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('ticket-create-form')}"
                            """

    nav_title = _("Ticket Type")
    search_swap_target = "#listContainer"
    filter_instance = TicketTypeFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.add_tickettype"), name="dispatch")
class TicketTypeCreateForm(HorillaFormView):
    """
    form view for creating and update tickets in settings
    """

    model = TicketType
    form_class = TicketTypeForm
    new_display_title = _("Create Ticket Type")
    is_dynamic_create = True

    def get_context_data(self, **kwargs):
        """
        Add form to context, initializing with instance if it exists.
        """
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Ticket Type")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        """
        Handles and renders form errors or defers to superclass.
        """
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Ticket Type")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: TicketTypeForm) -> HttpResponse:
        """
        Handle valid form submission.
        """
        if form.is_valid():
            if form.instance.pk:
                messages.success(
                    self.request, _("Ticket type has been updated successfully!")
                )
            else:
                messages.success(
                    self.request, _("Ticket type has been created successfully!")
                )
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class TicketsCreateFormView(HorillaFormView):
    """
    form view for create and update tickets
    """

    model = Ticket
    form_class = TicketForm
    new_display_title = _("Create Ticket")
    template_name = "cbv/tickets/inherit_form.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.request.user.has_perm("helpdesk.add_tickettype"):
            self.dynamic_create_fields = [
                ("ticket_type", TicketTypeCreateForm),
                ("tags", DynamicTagsCreateFormView),
            ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form.fields["employee_id"].initial = self.request.user.employee_get
        status = self.request.GET.get("status")
        self.form.fields["status"].initial = status
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Ticket")
        context["form"] = self.form
        return context

    def form_valid(self, form: TicketForm) -> HttpResponse:
        if form.is_valid():
            if not form.instance.pk:
                ticket = form.save()
                attachments = form.files.getlist("attachment")
                for attachment in attachments:
                    attachment_instance = Attachment(file=attachment)
                    attachment_instance.save()
                mail_thread = TicketSendThread(self.request, ticket, type="create")
                mail_thread.start()
                messages.success(self.request, _("The Ticket created successfully."))
                employees = ticket.assigned_to.all()
                assignees = [employee.employee_user_id for employee in employees]
                assignees.append(ticket.employee_id.employee_user_id)

                if ticket.assigning_type == "individual":
                    try:
                        employee = Employee.objects.get(
                            id=ticket.raised_on
                        )  # adjust if raised_on stores badge_id etc.
                        ticket.assigned_to.set([employee])
                        ticket.save()
                    except Employee.DoesNotExist:
                        print(f"No employee found with identifier: {ticket.raised_on}")

                employees = ticket.assigned_to.all()
                assignees = [emp.employee_user_id for emp in employees]
                assignees.append(ticket.employee_id.employee_user_id)

                if (
                    hasattr(ticket.get_raised_on_object(), "dept_manager")
                    and not ticket.assigning_type == "individual"
                ):
                    if ticket.get_raised_on_object().dept_manager.all():
                        manager = (
                            ticket.get_raised_on_object()
                            .dept_manager.all()
                            .first()
                            .manager
                        )
                        assignees.append(manager.employee_user_id)
                notify.send(
                    self.request.user.employee_get,
                    recipient=assignees,
                    verb="You have been assigned to a new Ticket",
                    verb_ar="لقد تم تعيينك لتذكرة جديدة",
                    verb_de="Ihnen wurde ein neues Ticket zugewiesen",
                    verb_es="Se te ha asignado un nuevo ticket",
                    verb_fr="Un nouveau ticket vous a été attribué",
                    icon="infinite",
                    redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                )
            else:
                ticket = form.save()
                messages.success(self.request, _("The Ticket updated successfully."))

            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)
