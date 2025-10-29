import json
import logging
import string
import threading
from typing import Iterable

from bs4 import BeautifulSoup
from django.contrib import messages
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from base.models import Announcement
from employee.models import Employee
from horilla.decorators import check_integration_enabled
from horilla.horilla_middlewares import _thread_locals
from notifications.signals import notify
from whatsapp.flows import (
    get_asset_category_flow_json,
    get_attendance_request_json,
    get_bonus_point_json,
    get_leave_request_json,
    get_reimbursement_request_json,
    get_shift_request_json,
    get_work_type_request_json,
)
from whatsapp.models import WhatsappCredientials
from whatsapp.utils import (
    asset_request_create,
    attendance_request_create,
    bonus_point_create,
    create_flow,
    create_help_message,
    create_template_buttons,
    create_welcome_message,
    leave_request_create,
    publish_flow,
    reimbursement_create,
    send_document_message,
    send_flow_message,
    send_image_message,
    send_template_message,
    send_text_message,
    shift_create,
    update_flow,
    work_type_create,
)

DETAILED_FLOW = [
    {
        "template_name": "leave",
        "flow_name": "leave_request_flow",
        "flow_json": get_leave_request_json(),
    },
    {
        "template_name": "shift",
        "flow_name": "shift_request",
        "flow_json": get_shift_request_json(),
    },
    {
        "template_name": "bonus_point",
        "flow_name": "bonus_point_flow",
        "flow_json": get_bonus_point_json(),
    },
    {
        "template_name": "reimbursement",
        "flow_name": "reimbursement_flow",
        "flow_json": get_reimbursement_request_json(),
    },
    {
        "template_name": "work_type",
        "flow_name": "work_type_flow",
        "flow_json": get_work_type_request_json(),
    },
    {
        "template_name": "attendance",
        "flow_name": "attendance_flow",
        "flow_json": get_attendance_request_json(),
    },
    {
        "template_name": "asset",
        "flow_name": "asset_flow",
        "flow_json": get_asset_category_flow_json(),
    },
]

processed_messages = set()
logger = logging.getLogger(__name__)


def clean_string(s):
    """
    Cleans a given string by removing punctuation and converting it to lowercase.

    Args:
        s (str): The string to clean.

    Returns:
        str: The cleaned string, or the original string if an error occurs.
    """

    try:
        translator = str.maketrans("", "", string.punctuation + " _")
        cleaned_string = s.translate(translator).lower()
        return cleaned_string
    except:
        return s


@csrf_exempt
@check_integration_enabled(app_name="whatsapp")
def whatsapp(request):
    """
    Handles incoming WhatsApp webhook requests.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: A response indicating the status of the operation.
    """

    if request.method == "GET":
        credentials = WhatsappCredientials.objects.first()

        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if token == credentials.meta_webhook_token:
            return HttpResponse(challenge, status=200)

    if request.method == "POST":
        data = json.loads(request.body)
        if "object" in data and "entry" in data:
            if data["object"] == "whatsapp_business_account":
                for entry in data["entry"]:
                    changes = entry.get("changes", [])[0]
                    value = changes.get("value", {})

                    if "messages" in value:
                        try:
                            metadata = value.get("metadata", {})
                            contacts = value.get("contacts", [])[0]
                            messages = value.get("messages", [])[0]

                            message_id = messages.get("id")
                            if message_id in processed_messages:
                                continue

                            processed_messages.add(message_id)

                            profile_name = contacts.get("profile", {}).get("name")
                            from_number = messages.get("from")
                            text = messages.get("text", {}).get("body")
                            type = messages.get("type", {})
                            flow_response = (
                                messages.get("interactive", {})
                                .get("nfm_reply", {})
                                .get("response_json", {})
                            )

                            if type == "interactive":
                                flow_conversion(from_number, flow_response)
                            if type == "button":
                                text = messages.get("button", {}).get("text", {})

                            text = clean_string(text)

                            # Handle different messages based on cleaned text
                            if text == "helloworld":
                                send_template_message(from_number, "hello_world")
                            elif text == "help":
                                send_template_message(from_number, "help_text")
                            elif text in ["asset", "assetrequest"]:
                                send_flow_message(from_number, "asset")
                            elif text in ["shift", "shiftrequest"]:
                                send_flow_message(from_number, "shift")
                            elif text in ["worktype", "worktyperequest"]:
                                send_flow_message(from_number, "work_type")
                            elif text in ["attendance", "attendancerequest"]:
                                send_flow_message(from_number, "attendance")
                            elif text in ["leave", "leaverequest"]:
                                send_flow_message(from_number, "leave")
                            elif text in ["reimbursement", "reimbursementrequest"]:
                                send_flow_message(from_number, "reimbursement")
                            elif text in ["bonus", "bonuspoint", "bonuspointredeem"]:
                                send_flow_message(from_number, "bonus_point")
                            elif text in [
                                "hi",
                                "hello",
                                "goodmorning",
                                "goodafternoon",
                                "goodevening",
                                "goodnight",
                                "hlo",
                            ]:
                                send_template_message(from_number, "welcome_message")
                            elif text == "image":
                                try:
                                    image_relative_url = (
                                        Employee.objects.filter(phone=from_number)
                                        .first()
                                        .employee_profile.url
                                    )
                                    image_link = request.build_absolute_uri(
                                        image_relative_url
                                    )
                                except Exception as e:
                                    print(e)

                                send_image_message(from_number, image_link)
                            elif text == "document":
                                try:
                                    document_relative_url = (
                                        Employee.objects.filter(phone=from_number)
                                        .first()
                                        .employee_profile.url
                                    )
                                    document_link = request.build_absolute_uri(
                                        document_relative_url
                                    )
                                except Exception as e:
                                    print(e)

                                send_document_message(from_number, document_link)
                            elif text == "string":
                                send_text_message(
                                    from_number, "test message", "test heading"
                                )
                            else:
                                if text:
                                    send_template_message(
                                        from_number, "button_template"
                                    )

                        except KeyError as e:
                            print(f"KeyError: {e}")
                            return HttpResponse("Bad Request", status=400)
                        except Exception as e:
                            print(f"Unexpected error: {e}")
                            return HttpResponse("Internal Server Error", status=500)

                        return HttpResponse("Message processed", status=403)

    return HttpResponse("error", status=200)


@check_integration_enabled(app_name="whatsapp")
def create_generic_templates(request, id):
    """
    Creates generic message templates for WhatsApp.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: A response indicating the success or failure of template creation.
    """

    flag = True
    try:
        create_template_buttons(id)
    except Exception as e:
        flag = False
        messages.error(request, e)

    try:
        create_welcome_message(id)
    except Exception as e:
        flag = False
        messages.error(request, e)

    try:
        create_help_message(id)
    except Exception as e:
        flag = False
        messages.error(request, e)

    try:
        create_flows(id)
    except Exception as e:
        flag = False
        messages.error(request, e)

    if flag:
        credential = WhatsappCredientials.objects.get(id=id)
        credential.created_templates = True
        credential.save()

        messages.success(request, "Message templates and flows created successfully.")
    return HttpResponse("<script>window.location.reload();</script>")


# @csrf_exempt
# def create_flows(cred_id):
#     """
#     Creates and publishes flows based on predefined details.

#     Args:
#         request (HttpRequest): The incoming HTTP request.

#     Returns:
#         HttpResponse: A response indicating the success or failure of flow creation.
#     """

#     try:
#         for flow in DETAILED_FLOW:
#             template_name = flow["template_name"]
#             flow_name = flow["flow_name"]
#             flow_json = flow["flow_json"]
#             credential = WhatsappCredientials.objects.get(id=cred_id)

#             # Create flow
#             create_response = create_flow(flow_name, template_name, cred_id)
#             create_response_data = create_response.json()

#             flow_id = create_response_data.get("id")
#             if not flow_id:
#                 return HttpResponse(
#                     json.dumps(create_response_data),
#                     status=create_response.status_code,
#                     content_type="application/json",
#                 )

#             # Update flow
#             update_response = update_flow(flow_id, flow_json,credential.meta_token)
#             update_response_data = update_response.json()
#             if update_response_data.get("validation_error", {}):
#                 return HttpResponse(
#                     json.dumps(update_response_data),
#                     status=update_response.status_code,
#                     content_type="application/json",
#                 )

#             # Publish flow
#             publish_response = publish_flow(flow_id,credential.meta_token)
#             publish_response_data = publish_response.json()
#             if publish_response_data.get("error", {}):
#                 return HttpResponse(
#                     json.dumps(publish_response_data),
#                     status=publish_response.status_code,
#                     content_type="application/json",
#                 )

#         return HttpResponse(
#             json.dumps({"message": "Flow created successfully"}),
#             status=200,
#             content_type="application/json",
#         )

#     except Exception as e:
#         print(f"Unexpected error: {e}")
#         return HttpResponse(
#             json.dumps({"error": str(e)}), status=500, content_type="application/json"
#         )


@check_integration_enabled(app_name="whatsapp")
def create_flows(cred_id):
    """
    Creates and publishes flows based on predefined details.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: A response indicating the success or failure of flow creation.
    """
    for flow in DETAILED_FLOW:
        template_name = flow["template_name"]
        flow_name = flow["flow_name"]
        flow_json = flow["flow_json"]
        credential = WhatsappCredientials.objects.get(id=cred_id)

        # 1. Create flow
        create_data = create_flow(flow_name, template_name, cred_id)
        flow_id = create_data.get("id")
        if not flow_id:
            raise Exception(f"Flow ID missing after creation: {create_data}")

        # 2. Update flow
        update_data = update_flow(flow_id, flow_json, credential.meta_token)

        # 3. Publish flow
        publish_data = publish_flow(flow_id, credential.meta_token)

    return {"message": "Flows created, updated, and published successfully."}


def send_notification_task(request, recipient, verb, redirect, icon):
    """
    Background task to send a notification message via WhatsApp.
    """
    try:
        link = request.build_absolute_uri(redirect) if redirect else None
        message = f"{verb}\nFor more details, \n{link}." if link else verb

        recipients = (
            recipient
            if isinstance(recipient, Iterable) and not isinstance(recipient, str)
            else [recipient]
        )

        for user in recipients:
            phone_number = user.employee_get.phone
            if phone_number:
                send_text_message(phone_number, message)
            else:
                print(f"No phone number available for recipient {user}")

    except Exception as e:
        print(f"Error in notification task: {e}")


@receiver(notify)
@check_integration_enabled(app_name="whatsapp")
def send_notification_on_whatsapp(sender, recipient, verb, redirect, icon, **kwargs):

    request = getattr(_thread_locals, "request", None)
    thread = threading.Thread(
        target=send_notification_task, args=(request, recipient, verb, redirect, icon)
    )
    thread.start()


def send_announcement_task(instance, request):
    """
    Background task to send an announcement message via WhatsApp.
    """
    employees = instance.employees.all()
    header = instance.title
    body = instance.description

    soup = BeautifulSoup(body, "html.parser")
    paragraphs = []
    for element in soup.find_all(["p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"]):
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            heading_text = element.get_text(strip=True).capitalize()
            paragraphs.append(f"*{heading_text}*")

        elif element.name in ["ul", "ol"]:
            list_items = []
            for li in element.find_all("li"):
                item_text = []
                for child in li.children:
                    if child.name == "code":
                        item_text.append(f"`{child.get_text()}`")
                    elif child.name in ["strong", "b"]:
                        item_text.append(f"*{child.get_text()}*")
                    elif child.name == "span":
                        item_text.append(child.get_text())
                    elif child.name == "a":
                        item_text.append(child.get_text())
                    elif isinstance(child, str):
                        item_text.append(child.strip())
                list_items.append("• " + " ".join(item_text).strip())
            paragraphs.append("\n".join(list_items))

        elif element.name == "p":
            para_text = []
            for child in element.children:
                if child.name == "code":
                    para_text.append(f"`{child.get_text()}`")
                elif child.name in ["strong", "b"]:
                    para_text.append(f"*{child.get_text()}*")
                elif child.name == "span":
                    para_text.append(child.get_text())
                elif child.name == "a":
                    para_text.append(child.get_text())
                elif isinstance(child, str):
                    para_text.append(child.strip())
            paragraphs.append(" ".join(para_text).strip())
    final_text = "\n\n".join(paragraphs)

    for employee in employees:
        number = employee.phone
        send_text_message(number, final_text, header)
        for attachment in instance.attachments.all():
            link = attachment.file.url
            document_link = request.build_absolute_uri(link)
            send_document_message(number, document_link)


def send_announcement(instance):
    """
    Helper: send announcement only once after both M2Ms are set.
    """
    if (
        getattr(instance, "_created", False)
        and getattr(instance, "_employees_added", False)
        and getattr(instance, "_attachments_added", False)
    ):
        request = getattr(_thread_locals, "request", None)

        thread = threading.Thread(
            target=send_announcement_task,
            args=(instance, request),
            daemon=True,
        )
        thread.start()

        # Reset flags
        instance._created = False
        instance._employees_added = False
        instance._attachments_added = False


# @receiver(post_save, sender=Announcement)
@check_integration_enabled(app_name="whatsapp")
def mark_announcement_created(sender, instance, created, **kwargs):
    if created:
        # Temporary flags to track both M2M relations
        instance._created = True
        instance._employees_added = False
        instance._attachments_added = False


# @receiver(m2m_changed, sender=Announcement.employees.through)
@check_integration_enabled(app_name="whatsapp")
def employees_m2m_changed(sender, instance, action, **kwargs):
    if action == "post_add" and getattr(instance, "_created", False):
        instance._employees_added = True
        send_announcement(instance)


# @receiver(m2m_changed, sender=Announcement.attachments.through)
@check_integration_enabled(app_name="whatsapp")
def attachments_m2m_changed(sender, instance, action, **kwargs):
    if action == "post_add" and getattr(instance, "_created", False):
        instance._attachments_added = True
        send_announcement(instance)


@check_integration_enabled(app_name="whatsapp")
def flow_conversion(number, flow_response_json):
    """
    Processes a flow response based on the type of request.

    Args:
        number (str): The phone number of the employee.
        flow_response_json (str): The JSON response from the flow.

    Returns:
        Response: The response from sending a message.
    """

    employee = Employee.objects.filter(phone=number).first()
    flow_response = json.loads(flow_response_json)
    message = "Something went wrong ......"
    type = flow_response["type"]

    if type == "shift_request":
        message = shift_create(employee, flow_response)
    elif type == "leave_request":
        message = leave_request_create(employee, flow_response)
    elif type == "work_type":
        message = work_type_create(employee, flow_response)
    elif type == "asset_request":
        message = asset_request_create(employee, flow_response)
    elif type == "attendance_request":
        message = attendance_request_create(employee, flow_response)
    elif type == "bonus_point":
        message = bonus_point_create(employee, flow_response)
    elif type == "reimbursement":
        message = reimbursement_create(employee, flow_response)

    response = send_text_message(number, message)
    return response
