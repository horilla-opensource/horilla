import json
import logging
import os
from datetime import datetime
from distutils.util import strtobool
from operator import itemgetter
from urllib.parse import parse_qs

from django.conf import settings
from django.contrib import messages
from django.core import serializers
from django.db.models import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from base.forms import TagsForm
from base.methods import (
    filtersubordinates,
    get_key_instances,
    is_reportingmanager,
    paginator_qry,
    sortby,
)
from base.models import Department, JobPosition, Tags
from employee.models import Employee
from employee.views import get_content_type
from helpdesk.decorators import ticket_owner_can_enter
from helpdesk.filter import (
    FAQCategoryFilter,
    FAQFilter,
    FaqSearch,
    TicketFilter,
    TicketReGroup,
)
from helpdesk.forms import (
    AttachmentForm,
    CommentForm,
    DepartmentManagerCreateForm,
    FAQCategoryForm,
    FAQForm,
    TicketAssigneesForm,
    TicketForm,
    TicketRaisedOnForm,
    TicketTagForm,
    TicketTypeForm,
)
from helpdesk.methods import is_department_manager
from helpdesk.models import (
    FAQ,
    TICKET_STATUS,
    Attachment,
    ClaimRequest,
    Comment,
    DepartmentManager,
    FAQCategory,
    Ticket,
    TicketType,
)
from helpdesk.threading import AddAssigneeThread, RemoveAssigneeThread, TicketSendThread
from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from horilla.group_by import group_by_queryset
from notifications.signals import notify

logger = logging.getLogger(__name__)

# Create your views here.


@login_required
def faq_category_view(request):
    """
    This function is responsible for rendering the FAQ category view.

    Parameters:
        request (HttpRequest): The HTTP request object.
    """

    faq_categories = FAQCategory.objects.all()
    questions = FAQ.objects.values_list("question", flat=True)
    context = {
        "faq_categories": faq_categories,
        "questions": list(questions),
    }

    return render(request, "helpdesk/faq/faq_view.html", context=context)


@login_required
@hx_request_required
@permission_required("helpdesk.add_faqcategory")
def faq_category_create(request):
    """
    This function is responsible for creating the FAQ Category.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return faq category create form template
    POST : return faq category view
    """

    form = FAQCategoryForm()
    if request.method == "POST":
        form = FAQCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("The FAQ Category created successfully."))
            form = FAQCategoryForm()

    context = {
        "form": form,
    }
    return render(request, "helpdesk/faq/faq_category_create.html", context)


@login_required
@hx_request_required
@permission_required("helpdesk.change_faqcategory")
def faq_category_update(request, id):
    """
    This function is responsible for updating the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.
        id : id of the faq to update.

    Returns:
    GET : return faq create form template
    POST : return faq view
    """

    faq_category = FAQCategory.objects.get(id=id)
    form = FAQCategoryForm(instance=faq_category)
    if request.method == "POST":
        form = FAQCategoryForm(request.POST, instance=faq_category)
        if form.is_valid():
            form.save()
            messages.success(request, _("The FAQ category updated successfully."))

    context = {
        "form": form,
        "faq_category": faq_category,
    }
    return render(request, "helpdesk/faq/faq_category_create.html", context)


@login_required
@permission_required("helpdesk.delete_faqcategory")
def faq_category_delete(request, id):
    try:
        faq = FAQCategory.objects.get(id=id)
        faq.delete()
        messages.success(request, _("The FAQ category has been deleted successfully."))
        return HttpResponse("")
    except ProtectedError:
        messages.error(request, _("You cannot delete this FAQ category."))
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
@hx_request_required
def faq_category_search(request):
    """
    This function is responsible for search and filter the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return faq filter form template
    POST : return faq view
    """

    previous_data = request.GET.urlencode()
    faq_categories = FAQCategoryFilter(request.GET).qs
    data_dict = parse_qs(previous_data)
    get_key_instances(FAQCategory, data_dict)
    context = {
        "faq_categories": faq_categories,
        "f": FAQCategoryFilter(request.GET),
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, "helpdesk/faq/faq_category_list.html", context)


@login_required
def faq_view(request, obj_id, **kwargs):
    """
    This function is responsible for rendering the FAQ view.

    Parameters:
        request (HttpRequest): The HTTP request object.
        obj_id (int): The id of the the faq category.
    """

    faqs = FAQ.objects.filter(category=obj_id)
    faq_category = FAQCategory.objects.filter(id=obj_id)
    if not faq_category:
        messages.info(request, _("No FAQ found for the given category."))
        return redirect(faq_category_view)
    context = {
        "faqs": faqs,
        "f": FAQFilter(request.GET),
        "cat_id": obj_id,
        "create_tag_f": TagsForm(),
    }

    return render(request, "helpdesk/faq/faq_list_view.html", context=context)


@login_required
@hx_request_required
@permission_required("helpdesk.add_faq")
def create_faq(request, obj_id):
    """
    This function is responsible for creating the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return faq create form template
    POST : return faq view
    """

    form = FAQForm(initial={"category": obj_id})
    if request.method == "POST":
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("The FAQ created successfully."))

    context = {
        "form": form,
        "cat_id": obj_id,
    }
    return render(request, "helpdesk/faq/faq_create.html", context)


@login_required
@hx_request_required
@permission_required("helpdesk.change_faq")
def faq_update(request, obj_id):
    """
    This function is responsible for updating the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.
        id : id of the faq to update.

    Returns:
    GET : return faq create form template
    POST : return faq view
    """

    faq = FAQ.objects.get(id=obj_id)
    form = FAQForm(instance=faq)
    if request.method == "POST":
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, _("The FAQ updated successfully."))
    context = {
        "form": form,
        "faq": faq,
        "cat_id": faq.category.id,
    }
    return render(request, "helpdesk/faq/faq_create.html", context)


@login_required
@hx_request_required
def faq_search(request):
    """
    This function is responsible for search and filter the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return faq filter form template
    POST : return faq view
    """
    id = request.GET.get("cat_id", "")
    category = request.GET.get("category", "")
    previous_data = request.GET.urlencode()
    query = request.GET.get("search", "")
    data_dict = parse_qs(previous_data)
    get_key_instances(FAQ, data_dict)

    if query:
        faqs = FaqSearch(request.GET).qs

    else:
        faqs = FAQ.objects.filter(is_active=True)
        if category:
            return redirect(faq_category_search)

    if id:
        data_dict.pop("cat_id")
        faqs = faqs.filter(category=id)
    if category:
        data_dict.pop("category")

    context = {
        "faqs": faqs,
        "f": FAQFilter(request.GET),
        "pd": previous_data,
        "filter_dict": data_dict,
        "query": query,
    }
    return render(request, "helpdesk/faq/faq_list.html", context)


@login_required
@hx_request_required
def faq_filter(request, id):
    """
    This function is responsible for filter the FAQ.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return faq filter form template
    POST : return faq view
    """

    previous_data = request.GET.urlencode()
    faqs = FAQFilter(request.GET).qs
    faqs = faqs.filter(category=id)
    data_dict = parse_qs(previous_data)
    get_key_instances(FAQ, data_dict)
    context = {
        "faqs": faqs,
        "f": FAQFilter(request.GET),
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, "helpdesk/faq/faq_list.html", context)


@login_required
def faq_suggestion(request):
    faqs = FAQFilter(request.GET).qs
    data_list = list(faqs.values())
    response = {
        "faqs": data_list,
    }
    return JsonResponse(response)


@login_required
@permission_required("helpdesk.delete_faq")
def faq_delete(request, id):
    try:
        faq = FAQ.objects.get(id=id)
        cat_id = faq.category.id
        faq.delete()
        messages.success(
            request, _('The FAQ "{}" has been deleted successfully.').format(faq)
        )
        return HttpResponse("")
    except ProtectedError:
        messages.error(request, _("You cannot delete this FAQ."))
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
def ticket_view(request):
    """
    This function is responsible for rendering the Ticket view.

    Parameters:
        request (HttpRequest): The HTTP request object.
    """
    tickets = Ticket.objects.filter(is_active=True)
    view = request.GET.get("view") if request.GET.get("view") else "list"
    employee = request.user.employee_get
    previous_data = request.GET.urlencode()
    my_page_number = request.GET.get("my_page")
    all_page_number = request.GET.get("all_page")
    allocated_page_number = request.GET.get("allocated_page")

    my_tickets = tickets.filter(employee_id=employee) | tickets.filter(
        created_by=request.user
    )
    all_tickets = []
    if is_reportingmanager(request):
        all_tickets = filtersubordinates(request, tickets, "helpdesk.view_ticket")
    if request.user.has_perm("helpdesk.view_ticket"):
        all_tickets = tickets
    allocated_tickets = []
    ticket_list = tickets.filter(is_active=True)
    user = request.user.employee_get
    if hasattr(user, "employee_work_info"):
        department = user.employee_work_info.department_id
        job_position = user.employee_work_info.job_position_id
        if department:
            tickets_items = ticket_list.filter(
                raised_on=department.id, assigning_type="department"
            )
            allocated_tickets += tickets_items
        if job_position:
            tickets_items = ticket_list.filter(
                raised_on=job_position.id, assigning_type="job_position"
            )
            allocated_tickets += tickets_items

    tickets_items = ticket_list.filter(raised_on=user.id, assigning_type="individual")
    allocated_tickets += tickets_items

    data_dict = parse_qs(previous_data)
    get_key_instances(Ticket, data_dict)
    template = "helpdesk/ticket/ticket_view.html"
    context = {
        "my_tickets": paginator_qry(my_tickets, my_page_number),
        "all_tickets": paginator_qry(all_tickets, all_page_number),
        "allocated_tickets": paginator_qry(allocated_tickets, allocated_page_number),
        "f": TicketFilter(request.GET),
        "gp_fields": TicketReGroup.fields,
        "ticket_status": TICKET_STATUS,
        "view": view,
        "today": datetime.today().date(),
        "filter_dict": data_dict,
    }

    return render(request, template, context=context)


@login_required
@hx_request_required
def ticket_create(request):
    """
    This function is responsible for creating the Ticket.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Ticket create form template
    POST : return Ticket view
    """

    form = TicketForm()
    if request.GET.get("status"):
        status = request.GET.get("status")
        form = TicketForm(
            initial={
                "status": status,
            }
        )
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save()
            attachments = form.files.getlist("attachment")
            for attachment in attachments:
                attachment_instance = Attachment(file=attachment, ticket=ticket)
                attachment_instance.save()
            mail_thread = TicketSendThread(request, ticket, type="create")
            mail_thread.start()
            messages.success(request, _("The Ticket created successfully."))
            employees = ticket.assigned_to.all()
            assignees = [employee.employee_user_id for employee in employees]
            assignees.append(ticket.employee_id.employee_user_id)
            if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                if ticket.get_raised_on_object().dept_manager.all():
                    manager = (
                        ticket.get_raised_on_object().dept_manager.all().first().manager
                    )
                    assignees.append(manager.employee_user_id)
            notify.send(
                request.user.employee_get,
                recipient=assignees,
                verb="You have been assigned to a new Ticket",
                verb_ar="لقد تم تعيينك لتذكرة جديدة",
                verb_de="Ihnen wurde ein neues Ticket zugewiesen",
                verb_es="Se te ha asignado un nuevo ticket",
                verb_fr="Un nouveau ticket vous a été attribué",
                icon="infinite",
                redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
            )
            return HttpResponse("<script>window.location.reload()</script>")
    context = {
        "form": form,
        "t_type_form": TicketTypeForm(),
    }
    return render(request, "helpdesk/ticket/ticket_form.html", context)


@login_required
@hx_request_required
def ticket_update(request, ticket_id):
    """
    This function is responsible for updating the Ticket.

    Parameters:
        request (HttpRequest): The HTTP request object.
        ticket_id : id of the ticket to update.
    Returns:
    GET : return Ticket update form template
    POST : return Ticket view
    """

    ticket = Ticket.objects.get(id=ticket_id)
    if (
        request.user.has_perm("helpdesk.change_ticket")
        or is_department_manager(request, ticket)
        or request.user.employee_get == ticket.employee_id
        or request.user.employee_get in ticket.assigned_to.all()
    ):
        form = TicketForm(instance=ticket)
        if request.method == "POST":
            form = TicketForm(request.POST, request.FILES, instance=ticket)
            if form.is_valid():
                ticket = form.save()
                attachments = form.files.getlist("attachment")
                for attachment in attachments:
                    attachment_instance = Attachment(file=attachment, ticket=ticket)
                    attachment_instance.save()
                messages.success(request, _("The Ticket updated successfully."))
                return HttpResponse("<script>window.location.reload()</script>")
        context = {
            "form": form,
            "ticket_id": ticket_id,
            "t_type_form": TicketTypeForm(),
        }
        return render(request, "helpdesk/ticket/ticket_form.html", context)
    else:
        messages.info(request, _("You don't have permission."))

        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
def ticket_archive(request, ticket_id):
    """
    This function is responsible for archiving the Ticket.

    Parameters:
        request (HttpRequest): The HTTP request object.
        ticket_id : id of the ticket to update.
    Returns:
        return Ticket view
    """

    ticket = Ticket.objects.get(id=ticket_id)

    # Check if the user has permission or is the employee or their reporting manager
    if (
        request.user.has_perm("helpdesk.change_ticket")
        or ticket.employee_id == request.user.employee_get
        or is_department_manager(request, ticket)
    ):

        # Toggle the ticket's active state
        ticket.is_active = not ticket.is_active
        ticket.save()

        if ticket.is_active:
            messages.success(request, _("The Ticket un-archived successfully."))
        else:
            messages.success(request, _("The Ticket archived successfully."))

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        messages.info(request, _("You don't have permission."))

        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
# @ticket_owner_can_enter(perm="helpdesk.change_ticket", model=Ticket)
def change_ticket_status(request, ticket_id):
    """
    This function is responsible for changing the Ticket status.

    Parameters:
    request (HttpRequest): The HTTP request object.
    ticket_id (int): The ID of the Ticket

    Returns:
        return Ticket view
    """
    ticket = Ticket.objects.get(id=ticket_id)
    pre_status = ticket.get_status_display()
    status = request.POST.get("status")
    user = request.user.employee_get
    if ticket.status != status:
        if (
            user == ticket.employee_id
            or user in ticket.assigned_to.all()
            or request.user.has_perm("helpdesk.change_ticket")
        ):
            ticket.status = status
            ticket.save()
            time = datetime.now()
            time = time.strftime("%b. %d, %Y, %I:%M %p")
            response = {
                "type": "success",
                "message": _("The Ticket status updated successfully."),
                "user": user.get_full_name(),
                "pre_status": pre_status,
                "cur_status": ticket.get_status_display(),
                "time": time,
            }
            employees = ticket.assigned_to.all()
            assignees = [employee.employee_user_id for employee in employees]
            assignees.append(ticket.employee_id.employee_user_id)
            if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                if ticket.get_raised_on_object().dept_manager.all():
                    manager = (
                        ticket.get_raised_on_object().dept_manager.all().first().manager
                    )
                    assignees.append(manager.employee_user_id)
            notify.send(
                request.user.employee_get,
                recipient=assignees,
                verb=f"The status of the ticket has been changed to {ticket.status}.",
                verb_ar="تم تغيير حالة التذكرة.",
                verb_de="Der Status des Tickets wurde geändert.",
                verb_es="El estado del ticket ha sido cambiado.",
                verb_fr="Le statut du ticket a été modifié.",
                icon="infinite",
                redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
            )
            mail_thread = TicketSendThread(
                request,
                ticket,
                type="status_change",
            )
            mail_thread.start()
        else:
            response = {
                "type": "danger",
                "message": _("You Don't have the permission."),
            }

    if ticket.status == "resolved":
        ticket.resolved_date = datetime.today()
    return JsonResponse(response)


@login_required
@ticket_owner_can_enter(perm="helpdesk.delete_ticket", model=Ticket)
def ticket_delete(request, ticket_id):
    """
    This function is responsible for deleting the Ticket.

    Parameters:
    request (HttpRequest): The HTTP request object.
    ticket_id (int): The ID of the Ticket

    Returns:
    return Ticket view
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if ticket.status == "new":
            mail_thread = TicketSendThread(
                request,
                ticket,
                type="delete",
            )
            mail_thread.start()
            employees = ticket.assigned_to.all()
            assignees = [employee.employee_user_id for employee in employees]
            assignees.append(ticket.employee_id.employee_user_id)
            if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                if ticket.get_raised_on_object().dept_manager.all():
                    manager = (
                        ticket.get_raised_on_object().dept_manager.all().first().manager
                    )
                    assignees.append(manager.employee_user_id)
            notify.send(
                request.user.employee_get,
                recipient=assignees,
                verb=f"The ticket has been deleted.",
                verb_ar="تم حذف التذكرة.",
                verb_de="Das Ticket wurde gelöscht",
                verb_es="El billete ha sido eliminado.",
                verb_fr="Le ticket a été supprimé.",
                icon="infinite",
                redirect=reverse("ticket-view"),
            )
            ticket.delete()
            messages.success(
                request,
                _('The Ticket "{}" has been deleted successfully.').format(ticket),
            )
        else:
            messages.error(request, _('The ticket is not in the "New" status'))
    except ProtectedError:
        messages.error(request, _("You cannot delete this Ticket."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def get_allocated_tickets(request):
    user = request.user.employee_get
    department = user.employee_work_info.department_id
    job_position = user.employee_work_info.job_position_id

    tickets_items1 = Ticket.objects.filter(
        is_active=True, raised_on=department.id, assigning_type="department"
    )
    # allocated_tickets += tickets_items
    tickets_items2 = Ticket.objects.filter(
        is_active=True, raised_on=job_position.id, assigning_type="job_position"
    )
    # allocated_tickets += tickets_items
    tickets_items3 = Ticket.objects.filter(
        is_active=True, raised_on=user.id, assigning_type="individual"
    )
    # allocated_tickets += tickets_items
    allocated_tickets = tickets_items1 | tickets_items2 | tickets_items3
    return allocated_tickets


@login_required
@hx_request_required
def ticket_filter(request):
    """
    This function is responsible for search and filter the Ticket.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
    GET : return ticket filter form template
    POST : return ticket view
    """
    previous_data = request.GET.urlencode()
    tickets = TicketFilter(request.GET).qs
    my_page_number = request.GET.get("my_page")
    all_page_number = request.GET.get("all_page")
    allocated_page_number = request.GET.get("allocated_page")
    tickets_items1 = Ticket.objects.none()
    tickets_items2 = Ticket.objects.none()

    my_tickets = tickets.filter(employee_id=request.user.employee_get) | tickets.filter(
        created_by=request.user
    )

    all_tickets = tickets.filter(is_active=True)
    all_tickets = filtersubordinates(request, tickets, "helpdesk.add_tickets")
    if request.user.has_perm("helpdesk.view_ticket"):
        all_tickets = tickets

    allocated_tickets = Ticket.objects.none()
    user = request.user.employee_get
    department = user.employee_work_info.department_id
    job_position = user.employee_work_info.job_position_id
    ticket_list = tickets.filter(is_active=True)

    if hasattr(user, "employee_work_info"):
        department = user.employee_work_info.department_id
        job_position = user.employee_work_info.job_position_id
        if department:
            tickets_items1 = ticket_list.filter(
                raised_on=department.id, assigning_type="department"
            )
        if job_position:
            tickets_items2 = ticket_list.filter(
                raised_on=job_position.id, assigning_type="job_position"
            )

    tickets_items3 = ticket_list.filter(raised_on=user.id, assigning_type="individual")

    template = "helpdesk/ticket/ticket_list.html"

    if request.GET.get("view") == "card":
        template = "helpdesk/ticket/ticket_card.html"
    allocated_tickets = (
        list(tickets_items1) + list(tickets_items2) + list(tickets_items3)
    )
    if request.GET.get("sortby"):
        all_tickets = sortby(request, all_tickets, "sortby")
        my_tickets = sortby(request, my_tickets, "sortby")
        allocated_tickets = tickets_items1 | tickets_items2 | tickets_items3
        allocated_tickets = sortby(request, allocated_tickets, "sortby")

    field = request.GET.get("field")
    if field != "" and field is not None:
        my_tickets = group_by_queryset(
            my_tickets, field, request.GET.get("my_page"), "my_page"
        )
        all_tickets = group_by_queryset(
            all_tickets, field, request.GET.get("all_page"), "all_page"
        )
        tickets_items1 = group_by_queryset(
            tickets_items1, field, request.GET.get("allocated_page"), "allocated_page"
        )
        tickets_items2 = group_by_queryset(
            tickets_items2, field, request.GET.get("allocated_page"), "allocated_page"
        )
        tickets_items3 = group_by_queryset(
            tickets_items3, field, request.GET.get("allocated_page"), "allocated_page"
        )
        template = "helpdesk/ticket/ticket_group.html"
        allocated_tickets = (
            list(tickets_items1) + list(tickets_items2) + list(tickets_items3)
        )
    else:
        my_tickets = paginator_qry(my_tickets, my_page_number)
        all_tickets = paginator_qry(all_tickets, all_page_number)
        allocated_tickets = paginator_qry(allocated_tickets, allocated_page_number)

    data_dict = parse_qs(previous_data)
    get_key_instances(Ticket, data_dict)
    context = {
        "my_tickets": my_tickets,
        "all_tickets": all_tickets,
        "allocated_tickets": allocated_tickets,
        "f": TicketFilter(request.GET),
        "pd": previous_data,
        "ticket_status": TICKET_STATUS,
        "filter_dict": data_dict,
        "field": field,
        "today": datetime.today().date(),
    }

    return render(request, template, context)


@login_required
def ticket_detail(request, ticket_id, **kwargs):
    ticket = Ticket.objects.get(id=ticket_id)
    if (
        request.user.has_perm("helpdesk.view_ticket")
        or ticket.employee_id.get_reporting_manager() == request.user.employee_get
        or is_department_manager(request, ticket)
        or request.user.employee_get == ticket.employee_id
        or request.user.employee_get in ticket.assigned_to.all()
    ):
        today = datetime.now().date()
        c_form = CommentForm()
        f_form = AttachmentForm()
        attachments = ticket.ticket_attachment.all()

        activity_list = []
        comments = ticket.comment.all()
        trackings = ticket.tracking()
        for comment in comments:
            activity_list.append(
                {"type": "comment", "comment": comment, "date": comment.date}
            )
        for history in trackings:
            activity_list.append(
                {
                    "type": "history",
                    "history": history,
                    "date": history["pair"][0].history_date,
                }
            )

        sorted_activity_list = sorted(activity_list, key=itemgetter("date"))

        color = "success"
        remaining_days = ticket.deadline - today
        remaining = f"Due in {remaining_days.days} days"
        if remaining_days.days < 0:
            remaining = f"{abs(remaining_days.days)} days overdue"
            color = "danger"
        elif remaining_days.days == 0:
            remaining = "Due Today"
            color = "warning"

        rating = ""
        if ticket.priority == "low":
            rating = "1"
        elif ticket.priority == "medium":
            rating = "2"
        else:
            rating = "3"

        context = {
            "ticket": ticket,
            "c_form": c_form,
            "f_form": f_form,
            "attachments": attachments,
            "ticket_status": TICKET_STATUS,
            "tag_form": TicketTagForm(instance=ticket),
            "sorted_activity_list": sorted_activity_list,
            "create_tag_f": TagsForm(),
            "color": color,
            "remaining": remaining,
            "rating": rating,
        }
        return render(request, "helpdesk/ticket/ticket_detail.html", context=context)
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
def ticket_individual_view(request, ticket_id):
    ticket = Ticket.objects.filter(id=ticket_id).first()
    context = {
        "ticket": ticket,
    }
    return render(
        request, "helpdesk/ticket/ticket_individual_view.html", context=context
    )


@login_required
def view_ticket_claim_request(request, ticket_id):
    ticket = Ticket.objects.filter(id=ticket_id).first()
    if (
        request.user.has_perm("helpdesk.change_claimrequest")
        or request.user.has_perm("helpdesk.change_ticket")
        or is_department_manager(request, ticket)
    ):
        claim_requests = ticket.claimrequest_set.all()
        context = {
            "claim_requests": claim_requests,
        }
        return render(request, "helpdesk/ticket/ticket_claim_requests.html", context)
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
def ticket_update_tag(request):
    """
    method to update the tags of ticket
    """
    data = request.GET
    ticket = Ticket.objects.get(id=data["ticketId"])
    if (
        request.user.has_perm("helpdesk.view_ticket")
        or request.user.employee_get == ticket.employee_id
        or is_department_manager(request, ticket)
    ):
        tagids = data.getlist("selectedValues[]")
        ticket.tags.clear()
        for tagId in tagids:
            tag = Tags.objects.get(id=tagId)
            ticket.tags.add(tag)
        response = {
            "type": "success",
            "message": _("The Ticket tag updated successfully."),
        }
        return JsonResponse(response)
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
@hx_request_required
def ticket_change_raised_on(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)
    if (
        request.user.has_perm("helpdesk.view_ticket")
        or request.user.employee_get == ticket.employee_id
    ):
        form = TicketRaisedOnForm(instance=ticket)
        if request.method == "POST":
            form = TicketRaisedOnForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save()
                messages.success(request, _("Responsibility updated for the Ticket"))
                return redirect(ticket_detail, ticket_id=ticket_id)
        return render(
            request,
            "helpdesk/ticket/forms/change_raised_on.html",
            {"form": form, "ticket_id": ticket_id},
        )
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
@hx_request_required
def ticket_change_assignees(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)
    if request.user.has_perm("helpdesk.change_ticket") or is_department_manager(
        request, ticket
    ):
        prev_assignee_ids = ticket.assigned_to.values_list("id", flat=True)
        form = TicketAssigneesForm(instance=ticket)
        if request.method == "POST":
            form = TicketAssigneesForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save(commit=False)

                new_assignee_ids = form.cleaned_data["assigned_to"].values_list(
                    "id", flat=True
                )
                added_assignee_ids = set(new_assignee_ids) - set(prev_assignee_ids)
                removed_assignee_ids = set(prev_assignee_ids) - set(new_assignee_ids)
                added_assignees = Employee.objects.filter(id__in=added_assignee_ids)
                removed_assignees = Employee.objects.filter(id__in=removed_assignee_ids)

                form.save()

                mail_thread = AddAssigneeThread(
                    request,
                    ticket,
                    added_assignees,
                )
                mail_thread.start()
                mail_thread = RemoveAssigneeThread(
                    request,
                    ticket,
                    removed_assignees,
                )
                mail_thread.start()

                messages.success(request, _("Assinees updated for the Ticket"))
                return HttpResponse("<script>window.location.reload()</script>")

        return render(
            request,
            "helpdesk/ticket/forms/change_assinees.html",
            {"form": form, "ticket_id": ticket_id},
        )
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
def create_tag(request):
    """
    This is an ajax method to return json response to create tag in the change tag form.
    """

    if request.method == "POST":
        form = TagsForm(request.POST)

        if form.is_valid():
            instance = form.save()
            response = {
                "errors": "no_error",
                "tag_id": instance.id,
                "title": instance.title,
            }
            return JsonResponse(response)

        errors = form.errors.as_json()
        return JsonResponse({"errors": errors})


@login_required
def remove_tag(request):
    """
    This is an ajax method to  remove tag from a ticket.
    """

    data = request.GET
    ticket_id = data["ticket_id"]
    tag_id = data["tag_id"]
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        tag = Tags.objects.get(id=tag_id)
        ticket.tags.remove(tag)
        # message = messages.success(request,_("Success"))
        message = _("success")
        type = "success"
    except:
        message = messages.error(request, _("Failed"))

    return JsonResponse({"message": message, "type": type})


@login_required
@hx_request_required
def view_ticket_document(request, doc_id):
    """
    This function used to view the uploaded document in the modal.
    Parameters:

    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    Returns: return view_file template
    """

    document_obj = Attachment.objects.filter(id=doc_id).first()
    context = {
        "document": document_obj,
    }
    if document_obj.file:
        file_path = document_obj.file.path
        file_extension = os.path.splitext(file_path)[1][
            1:
        ].lower()  # Get the lowercase file extension
        content_type = get_content_type(file_extension)
        try:
            with open(file_path, "rb") as file:
                file_content = file.read()  # Decode the binary content for display
        except:
            file_content = None

        context["file_content"] = file_content
        context["file_extension"] = file_extension
        context["content_type"] = content_type
    return render(request, "helpdesk/ticket/ticket_document.html", context)


@login_required
@hx_request_required
def delete_ticket_document(request, doc_id):
    """
    This function used to delete the uploaded document in the modal.
    Parameters:

    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    """
    Attachment.objects.get(id=doc_id).delete()
    messages.success(request, _("Document has been deleted."))
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
def comment_create(request, ticket_id):
    """ "
    This method is used to create comment to a ticket
    """
    if request.method == "POST":
        ticket = Ticket.objects.get(id=ticket_id)
        c_form = CommentForm(request.POST)
        if c_form.is_valid():
            comment = c_form.save(commit=False)
            comment.employee_id = request.user.employee_get
            comment.ticket = ticket
            comment.save()
            if request.FILES:
                f_form = AttachmentForm(request.FILES)
                if f_form.is_valid():
                    files = request.FILES.getlist("file")
                    for file in files:
                        a_form = AttachmentForm(
                            {"file": file, "comment": comment, "ticket": ticket}
                        )
                        a_form.save()
            messages.success(request, _("A new comment has been created."))
    return redirect(ticket_detail, ticket_id=ticket_id)


@login_required
def comment_edit(request):
    comment_id = request.POST.get("comment_id")
    new_comment = request.POST.get("new_comment")
    if len(new_comment) > 1:
        comment = Comment.objects.get(id=comment_id)
        comment.comment = new_comment
        comment.save()
        messages.success(request, _("The comment updated successfully."))

    else:
        messages.error(request, _("The comment needs to be atleast 2 charactors."))
    response = {
        "errors": "no_error",
    }
    return JsonResponse(response)


@login_required
@permission_required("helpdesk.delete_comment")
def comment_delete(request, comment_id):
    comment = Comment.objects.filter(id=comment_id).first()
    employee = comment.employee_id
    comment.delete()
    messages.success(
        request, _("{}'s comment has been deleted successfully.").format(employee)
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def get_raised_on(request):
    """
    This is an ajax method to return list for raised on field.
    """
    data = request.GET
    assigning_type = data["assigning_type"]

    if assigning_type == "department":
        # Retrieve data from the Department model and format it as a list of dictionaries
        departments = Department.objects.values("id", "department")
        raised_on = [
            {"id": dept["id"], "name": dept["department"]} for dept in departments
        ]
    elif assigning_type == "job_position":
        jobpositions = JobPosition.objects.values("id", "job_position")
        raised_on = [
            {"id": job["id"], "name": job["job_position"]} for job in jobpositions
        ]
    elif assigning_type == "individual":
        employees = Employee.objects.values(
            "id", "employee_first_name", "employee_last_name"
        )
        raised_on = [
            {
                "id": employee["id"],
                "name": f"{employee['employee_first_name']} {employee['employee_last_name']}",
            }
            for employee in employees
        ]
    response = {"raised_on": list(raised_on)}
    return JsonResponse(response)


@login_required
def claim_ticket(request, id):
    """
    This is a function to create a claim request for requested employee
    """
    ticket = Ticket.objects.get(id=id)
    if not ClaimRequest.objects.filter(
        employee_id=request.user.employee_get, ticket_id=ticket
    ).exists():
        ClaimRequest(employee_id=request.user.employee_get, ticket_id=ticket).save()
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def approve_claim_request(request, req_id):
    """
    Function for approve claim request and send notifications to the responsibles.
    """
    claim_request = ClaimRequest.objects.filter(id=req_id).first()
    if not claim_request:
        return HttpResponse("Invalid claim request", status=404)

    approve = strtobool(
        request.GET.get("approve", "False")
    )  # Safely convert to boolean

    ticket = claim_request.ticket_id
    employee = claim_request.employee_id
    refresh = False
    if approve:
        # message
        message = _("Claim request approved successfully.")
        refresh = True
        if employee not in ticket.assigned_to.all():
            ticket.assigned_to.add(employee)  # Approve and assign to employee
            try:
                # send notification
                notify.send(
                    request.user.employee_get,
                    recipient=employee.employee_user_id,
                    verb=f"You have been assigned to a new Ticket-{ticket}.",
                    verb_ar=f"لقد تم تعيينك لتذكرة جديدة {ticket}.",
                    verb_de=f"Ihnen wurde ein neues Ticket {ticket} zugewiesen.",
                    verb_es=f"Se te ha asignado un nuevo ticket {ticket}.",
                    verb_fr=f"Un nouveau ticket {ticket} vous a été attribué.",
                    icon="infinite",
                    redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                )
            except Exception as e:
                logger.error(e)
            if not ticket.employee_id == ticket.created_by.employee_get:
                for emp in [ticket.created_by.employee_get, ticket.employee_id]:
                    try:
                        notify.send(
                            request.user.employee_get,
                            recipient=emp.employee_user_id,
                            verb=f"{employee} assigned to your ticket - {ticket}.",
                            verb_ar=f"تم تعيين {employee} إلى تذكرتك - {ticket}.",
                            verb_de=f"{employee} wurde Ihrem Ticket {ticket} zugewiesen.",
                            verb_es=f"{employee} ha sido asignado a tu ticket - {ticket}.",
                            verb_fr=f"{employee} a été assigné à votre ticket - {ticket}.",
                            icon="infinite",
                            redirect=reverse(
                                "ticket-detail", kwargs={"ticket_id": ticket.id}
                            ),
                        )
                    except Exception as e:
                        logger.error(e)
            try:
                notify.send(
                    request.user.employee_get,
                    recipient=ticket.employee_id.employee_user_id,
                    verb=f"{employee} assigned to your ticket - {ticket}.",
                    verb_ar=f"تم تعيين {employee} إلى تذكرتك - {ticket}.",
                    verb_de=f"{employee} wurde Ihrem Ticket {ticket} zugewiesen.",
                    verb_es=f"{employee} ha sido asignado a tu ticket - {ticket}.",
                    verb_fr=f"{employee} a été assigné à votre ticket - {ticket}.",
                    icon="infinite",
                    redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                )
            except Exception as e:
                logger.error(e)
    else:
        # message
        message = _("Claim request rejected successfully.")
        refresh = True
        if employee in ticket.assigned_to.all():
            ticket.assigned_to.remove(employee)  # Reject and remove from assignment

            # send notification
            notify.send(
                request.user.employee_get,
                recipient=employee.employee_user_id,
                verb=f"Your claim request is rejected for Ticket-{ticket}",
                verb_ar=f"تم رفض طلبك للمطالبة بالتذكرة {ticket}.",
                verb_de=f"Ihre Anspruchsanfrage für Ticket-{ticket} wurde abgelehnt.",
                verb_es=f"Tu solicitud de reclamación ha sido rechazada para el ticket {ticket}.",
                verb_fr=f"Votre demande de réclamation pour le ticket {ticket} a été rejetée.",
                icon="infinite",
            )
    ticket.save()
    claim_request.is_approved = approve
    claim_request.is_rejected = not approve
    claim_request.save()
    html = render_to_string(
        "helpdesk/ticket/ticket_claim_requests.html",
        {"claim_requests": ticket.claimrequest_set.all(), "refresh": refresh},
    )
    messages.success(request, message)
    return HttpResponse(html)


@login_required
def tickets_select_filter(request):
    """
    This method is used to return all the ids of the filtered tickets
    """
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}
    table = request.GET.get("tableName")
    user = request.user.employee_get

    tickets_filter = TicketFilter(
        filters, queryset=Ticket.objects.filter(is_active=True)
    )
    if page_number == "all":
        if table == "all":
            tickets_filter = TicketFilter(filters, queryset=Ticket.objects.all())
        elif table == "my":
            tickets_filter = TicketFilter(
                filters, queryset=Ticket.objects.filter(employee_id=user)
            )
        else:
            allocated_tickets = get_allocated_tickets(request)
            tickets_filter = TicketFilter(filters, queryset=allocated_tickets)

        # Get the filtered queryset
        filtered_tickets = tickets_filter.qs

        ticket_ids = [str(ticket.id) for ticket in filtered_tickets]
        total_count = filtered_tickets.count()

        context = {"ticket_ids": ticket_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
@permission_required("helpdesk.change_ticket")
def tickets_bulk_archive(request):
    """
    This is a ajax method used to archive bulk of Ticket instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = False
    if request.GET.get("is_active") == "True":
        is_active = True
    for ticket_id in ids:
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.is_active = is_active
        ticket.save()
    messages.success(request, _("The Ticket updated successfully."))
    previous_url = request.META.get("HTTP_REFERER", "/")
    script = f'<script>window.location.href = "{previous_url}"</script>'
    return HttpResponse(script)


@login_required
# @ticket_owner_can_enter("perms.helpdesk.helpdesk_change_ticket", Ticket)
@permission_required("helpdesk.delete_ticket")
def tickets_bulk_delete(request):
    """
    This is a ajax method used to delete bulk of Ticket instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for ticket_id in ids:
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            mail_thread = TicketSendThread(
                request,
                ticket,
                type="delete",
            )
            mail_thread.start()
            employees = ticket.assigned_to.all()
            assignees = [employee.employee_user_id for employee in employees]
            assignees.append(ticket.employee_id.employee_user_id)
            if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                if ticket.get_raised_on_object().dept_manager.all():
                    manager = (
                        ticket.get_raised_on_object().dept_manager.all().first().manager
                    )
                    assignees.append(manager.employee_user_id)
            notify.send(
                request.user.employee_get,
                recipient=assignees,
                verb=f"The ticket has been deleted.",
                verb_ar="تم حذف التذكرة.",
                verb_de="Das Ticket wurde gelöscht",
                verb_es="El billete ha sido eliminado.",
                verb_fr="Le ticket a été supprimé.",
                icon="infinite",
                redirect=reverse("ticket-view"),
            )
            ticket.delete()
            messages.success(
                request,
                _('The Ticket "{}" has been deleted successfully.').format(ticket),
            )
        except ProtectedError:
            messages.error(request, _("You cannot delete this Ticket."))
    previous_url = request.META.get("HTTP_REFERER", "/")
    script = f'<script>window.location.href = "{previous_url}"</script>'
    return HttpResponse(script)


@login_required
@hx_request_required
def create_department_manager(request):
    form = DepartmentManagerCreateForm()
    if request.method == "POST":
        form = DepartmentManagerCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("The department manager created successfully."))

            return HttpResponse("<script>window.location.reload()</script>")
    context = {
        "form": form,
    }
    return render(request, "department_managers/department_managers_form.html", context)


@login_required
@hx_request_required
def update_department_manager(request, dep_id):
    department_manager = DepartmentManager.objects.get(id=dep_id)
    form = DepartmentManagerCreateForm(instance=department_manager)
    if request.method == "POST":
        form = DepartmentManagerCreateForm(request.POST, instance=department_manager)
        if form.is_valid():
            form.save()
            messages.success(request, _("The department manager updated successfully."))
            return HttpResponse("<script>window.location.reload()</script>")
    context = {
        "form": form,
        "dep_id": dep_id,
    }
    return render(request, "department_managers/department_managers_form.html", context)


@login_required
@permission_required("helpdesk.delete_departmentmanager")
def delete_department_manager(request, dep_id):
    department_manager = DepartmentManager.objects.get(id=dep_id)
    department_manager.delete()
    messages.success(request, _("The department manager has been deleted successfully"))

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def update_priority(request, ticket_id):
    """
    This function is used to update the priority
    from the detailed view
    """
    ticket = Ticket.objects.get(id=ticket_id)
    if (
        request.user.has_perm("helpdesk.view_ticket")
        or ticket.employee_id.get_reporting_manager() == request.user.employee_get
        or is_department_manager(request, ticket)
        or request.user.employee_get == ticket.employee_id
        or request.user.employee_get in ticket.assigned_to.all()
    ):
        rating = request.POST.get("rating")

        if rating == "1":
            ticket.priority = "low"
        elif rating == "2":
            ticket.priority = "medium"
        else:
            ticket.priority = "high"
        ticket.save()
        messages.success(request, _("Priority updated successfully."))
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    else:
        messages.info(request, _("You don't have permission."))
        previous_url = request.META.get("HTTP_REFERER", "/")

        # Handle request for HTMX if needed
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        else:
            return HttpResponse(
                f'<script>window.location.href = "{previous_url}"</script>'
            )


@login_required
@permission_required("helpdesk.view_tickettype")
def ticket_type_view(request):
    """
    This method is used to show Ticket type
    """
    ticket_types = TicketType.objects.all()
    return render(
        request, "base/ticket_type/ticket_type.html", {"ticket_types": ticket_types}
    )


@login_required
# @hx_request_required
@permission_required("helpdesk.create_tickettype")
def ticket_type_create(request):
    """
    This method renders form and template to create Ticket type
    """
    form = TicketTypeForm()
    if request.method == "POST":
        form = TicketTypeForm(request.POST)
        if request.GET.get("ajax"):
            if form.is_valid():
                instance = form.save()
                response = {
                    "errors": "no_error",
                    "ticket_id": instance.id,
                    "title": instance.title,
                }
                return JsonResponse(response)

            errors = form.errors.as_json()
            return JsonResponse({"errors": errors})
        if form.is_valid():
            form.save()
            form = TicketTypeForm()
            messages.success(request, _("Ticket type has been created successfully!"))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "base/ticket_type/ticket_type_form.html",
        {
            "form": form,
        },
    )


@login_required
@hx_request_required
@permission_required("helpdesk.update_tickettype")
def ticket_type_update(request, t_type_id):
    """
    This method renders form and template to create Ticket type
    """
    ticket_type = TicketType.objects.get(id=t_type_id)
    form = TicketTypeForm(instance=ticket_type)
    if request.method == "POST":
        form = TicketTypeForm(request.POST, instance=ticket_type)
        if form.is_valid():
            form.save()
            form = TicketTypeForm()
            messages.success(request, _("Ticket type has been updated successfully!"))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "base/ticket_type/ticket_type_form.html",
        {"form": form, "t_type_id": t_type_id},
    )


@login_required
@require_http_methods(["POST", "DELETE"])
@permission_required("helpdesk.delete_tickettype")
def ticket_type_delete(request, t_type_id):
    ticket_type = TicketType.find(t_type_id)
    if ticket_type:
        ticket_type.delete()
        messages.success(request, _("Ticket type has been deleted successfully!"))
    else:
        messages.error(request, _("Ticket type not found"))
    return HttpResponse()


@login_required
@permission_required("helpdesk.view_departmentmanager")
def view_department_managers(request):
    model_class = DepartmentManager
    department_managers = model_class.objects.all()

    context = {
        "model": model_class,
        "department_managers": department_managers,
    }
    return render(request, "department_managers/department_managers.html", context)


@login_required
@permission_required("helpdesk.change_departmentmanager")
def get_department_employees(request):
    """
    Method to return employee in the department
    """
    department = (
        Department.objects.filter(id=request.GET.get("dep_id")).first()
        if request.GET.get("dep_id")
        else None
    )
    if department:
        employees_queryset = department.employeeworkinformation_set.all().values_list(
            "employee_id__id", "employee_id__employee_first_name"
        )
    else:
        employees_queryset = None
    employees = list(employees_queryset)
    context = {"employees": employees}
    employee_html = render_to_string("employee/employees_select.html", context)
    return HttpResponse(employee_html)


@login_required
def load_faqs(request):
    base_dir = settings.BASE_DIR
    faq_file = os.path.join(base_dir, "load_data", "faq.json")
    faq_category_file = os.path.join(base_dir, "load_data", "faq_category.json")
    tags_file = os.path.join(base_dir, "load_data", "tags.json")

    with open(faq_category_file, "r") as cats:
        faq_category_raw = json.load(cats)

    with open(tags_file, "r") as t:
        tags_raw = json.load(t)

    with open(faq_file, "r") as faqs:
        faq_raw = json.load(faqs)

    category_lookup = {item["pk"]: item["fields"]["title"] for item in faq_category_raw}

    tag_lookup = {item["pk"]: item["fields"]["title"] for item in tags_raw}

    if request.method == "POST":
        selected_ids = [int(k) for k in request.POST.keys() if k.isdigit()]
        selected_faqs = [a for a in faq_raw if a["pk"] in selected_ids]

        category_needed = [
            faq["fields"].get("category")
            for faq in selected_faqs
            if faq["fields"].get("category")
        ]

        tags_needed_list = [
            faq["fields"].get("tags")
            for faq in selected_faqs
            if faq["fields"].get("tags")
        ]
        tags_needed = [item for item_list in tags_needed_list for item in item_list]

        for category_json in faq_category_raw:
            if category_json["pk"] in category_needed:
                category_data = list(
                    serializers.deserialize("json", json.dumps([category_json]))
                )[0].object
                existing = FAQCategory.objects.filter(title=category_data.title).first()
                if not existing:
                    category_data.pk = None
                    category_data.save()

        for tag_json in tags_raw:
            if tag_json["pk"] in tags_needed:
                tag_data = list(
                    serializers.deserialize("json", json.dumps([tag_json]))
                )[0].object
                existing = Tags.objects.filter(title=tag_data.title).first()
                if not existing:
                    tag_data.pk = None
                    tag_data.save()

        for faq_json in selected_faqs:
            deserialized = list(
                serializers.deserialize("json", json.dumps([faq_json]))
            )[0]
            faq_obj = deserialized.object

            category_pk = faq_json["fields"].get("category")
            tag_pk = faq_json["fields"].get("tags")
            category_title = category_lookup.get(category_pk)
            tags_title = [tag_lookup.get(pk, "") for pk in tag_pk]
            category = FAQCategory.objects.filter(title=category_title).first()
            tags = Tags.objects.filter(title__in=tags_title)
            faq_obj.category = category

            if not FAQ.objects.filter(question=faq_obj.question).exists():
                faq_obj.pk = None
                faq_obj.save()
                faq_obj.tags.set(tags)

                messages.success(
                    request, f"Automation '{faq_obj.question}' created successfully."
                )
            else:
                messages.warning(
                    request, f"Automation '{faq_obj.question}' already exists."
                )

        script = """
            <script>
                $('.oh-modal--show').removeClass('oh-modal--show');
                $('#reloadMessagesButton').click();
                $('.filterButton').click();
            </script>
        """
        return HttpResponse(script)

    processed_faqs = []
    for faq in faq_raw:
        processed = faq.copy()

        category_pk = faq["fields"].get("category")
        tag_pk = faq["fields"].get("tags")
        processed["tags"] = [tag_lookup.get(pk, "") for pk in tag_pk]
        processed["category"] = category_lookup.get(category_pk, "")
        processed_faqs.append(processed)

    return render(
        request,
        "helpdesk/faq/load_faq.html",
        {
            "faqs": processed_faqs,
            "catagories": category_lookup,
        },
    )
