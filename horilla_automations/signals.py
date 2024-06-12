"""
horilla_automation/signals.py

"""

import copy
import threading
import types
from django import template
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db.models.query import QuerySet
from django.db import models
from django.core.mail import EmailMessage
from base.thread_local_middleware import _thread_locals
from horilla.signals import pre_bulk_update, post_bulk_update


@classmethod
def from_list(cls, object_list):
    # Create a queryset-like object from the list
    queryset_like_object = cls(model=object_list[0].__class__)
    queryset_like_object._result_cache = list(object_list)
    queryset_like_object._prefetch_related_lookups = ()
    return queryset_like_object


setattr(QuerySet, "from_list", from_list)

SIGNAL_HANDLERS = []
INSTANCE_HANDLERS = []


def start_automation():
    """
    Automation signals
    """
    from horilla_automations.models import MailAutomation
    from horilla_automations.methods.methods import (
        split_query_string,
        get_model_class,
    )

    @receiver(post_delete, sender=MailAutomation)
    @receiver(post_save, sender=MailAutomation)
    def automation_pre_create(sender, instance, **kwargs):
        """
        signal method to handle automation post save
        """
        start_connection()
        track_previous_instance()

    def clear_connection():
        """
        Method to clear signals handlers
        """
        for handler in SIGNAL_HANDLERS:
            post_save.disconnect(handler, sender=handler.model_class)
            post_bulk_update.disconnect(handler, sender=handler.model_class)
        SIGNAL_HANDLERS.clear()

    def create_post_bulk_update_handler(automation, model_class, query_strings):
        def post_bulk_update_handler(sender, queryset, *args, **kwargs):
            def _bulk_update_thread_handler(
                queryset, previous_queryset_copy, automation
            ):
                request = getattr(queryset, "request", None)

                if request:
                    for index, instance in enumerate(queryset):
                        previous_instance = previous_queryset_copy[index]
                        send_automated_mail(
                            request,
                            False,
                            automation,
                            query_strings,
                            instance,
                            previous_instance,
                        )

            previous_bulk_record = getattr(_thread_locals, "previous_bulk_record", None)
            previous_queryset = None
            if previous_bulk_record:
                previous_queryset = previous_bulk_record["queryset"]
                previous_queryset_copy = previous_bulk_record["queryset_copy"]

            bulk_thread = threading.Thread(
                target=_bulk_update_thread_handler,
                args=(queryset, previous_queryset_copy, automation),
            )
            bulk_thread.start()

        func_name = f"{automation.method_title}_post_bulk_signal_handler"

        # Dynamically create a function with a unique name
        handler = types.FunctionType(
            post_bulk_update_handler.__code__,
            globals(),
            name=func_name,
            argdefs=post_bulk_update_handler.__defaults__,
            closure=post_bulk_update_handler.__closure__,
        )

        # Set additional attributes on the function
        handler.model_class = model_class
        handler.automation = automation

        return handler

    def start_connection():
        """
        Method to start signal connection accordingly to the automation
        """
        clear_connection()
        automations = MailAutomation.objects.filter(is_active=True)
        for automation in automations:

            condition_querystring = automation.condition_querystring.replace(
                "automation_multiple_", ""
            )

            query_strings = split_query_string(condition_querystring)

            model_path = automation.model
            model_class = get_model_class(model_path)

            handler = create_post_bulk_update_handler(
                automation, model_class, query_strings
            )
            SIGNAL_HANDLERS.append(handler)

            post_bulk_update.connect(handler, sender=model_class)

            def create_signal_handler(name, automation, query_strings):
                def signal_handler(sender, instance, created, **kwargs):
                    """
                    Signal handler for post-save events of the model instances.
                    """
                    request = getattr(_thread_locals, "request", None)
                    previous_record = getattr(_thread_locals, "previous_record", None)
                    previous_instance = None
                    if previous_record:
                        previous_instance = previous_record["instance"]

                    args = (
                        request,
                        created,
                        automation,
                        query_strings,
                        instance,
                        previous_instance,
                    )
                    thread = threading.Thread(
                        target=lambda: send_automated_mail(*args),
                    )
                    thread.start()

                signal_handler.__name__ = name
                signal_handler.model_class = model_class
                signal_handler.automation = automation
                return signal_handler

            # Create and connect the signal handler
            handler_name = f"{automation.method_title}_signal_handler"
            dynamic_signal_handler = create_signal_handler(
                handler_name, automation, query_strings
            )
            SIGNAL_HANDLERS.append(dynamic_signal_handler)
            post_save.connect(
                dynamic_signal_handler, sender=dynamic_signal_handler.model_class
            )

    def create_pre_bulk_update_handler(automation, model_class):
        def pre_bulk_update_handler(sender, queryset, *args, **kwargs):
            request = getattr(_thread_locals, "request", None)
            if request:
                _thread_locals.previous_bulk_record = {
                    "automation": automation,
                    "queryset": queryset,
                    "queryset_copy": QuerySet.from_list(copy.deepcopy(list(queryset))),
                }

        func_name = f"{automation.method_title}_pre_bulk_signal_handler"

        # Dynamically create a function with a unique name
        handler = types.FunctionType(
            pre_bulk_update_handler.__code__,
            globals(),
            name=func_name,
            argdefs=pre_bulk_update_handler.__defaults__,
            closure=pre_bulk_update_handler.__closure__,
        )

        # Set additional attributes on the function
        handler.model_class = model_class
        handler.automation = automation

        return handler

    def track_previous_instance():
        """
        method to add signal to track the automations model previous instances
        """

        def clear_instance_signal_connection():
            """
            Method to clear instance handler signals
            """
            for handler in INSTANCE_HANDLERS:
                pre_save.disconnect(handler, sender=handler.model_class)
                pre_bulk_update.disconnect(handler, sender=handler.model_class)
            INSTANCE_HANDLERS.clear()

        clear_instance_signal_connection()
        automations = MailAutomation.objects.filter(is_active=True)
        for automation in automations:
            model_class = get_model_class(automation.model)

            handler = create_pre_bulk_update_handler(automation, model_class)
            INSTANCE_HANDLERS.append(handler)
            pre_bulk_update.connect(handler, sender=model_class)

            @receiver(pre_save, sender=model_class)
            def instance_handler(sender, instance, **kwargs):
                """
                Signal handler for pres-save events of the model instances.
                """
                # prevented storing the scheduled activities
                request = getattr(_thread_locals, "request", None)
                if instance.pk:
                    # to get the previous instance
                    instance = model_class.objects.filter(id=instance.pk).first()
                if request:
                    _thread_locals.previous_record = {
                        "automation": automation,
                        "instance": instance,
                    }
                instance_handler.__name__ = (
                    f"{automation.method_title}_instance_handler"
                )
                return instance_handler

            instance_handler.model_class = model_class
            instance_handler.automation = automation

            INSTANCE_HANDLERS.append(instance_handler)

    track_previous_instance()
    start_connection()


def send_automated_mail(
    request,
    created,
    automation,
    query_strings,
    instance,
    previous_instance,
):
    from horilla_automations.methods.methods import evaluate_condition, operator_map
    from horilla_views.templatetags.generic_template_filters import getattribute

    applicable = False
    and_exists = False
    false_exists = False
    instance_values = []
    previous_instance_values = []
    for condition in query_strings:
        if condition.getlist("condition"):
            attr = condition.getlist("condition")[0]
            operator = condition.getlist("condition")[1]
            value = condition.getlist("condition")[2]

            if value == "on":
                value = True
            elif value == "off":
                value = False
            instance_value = getattribute(instance, attr)
            previous_instance_value = getattribute(previous_instance, attr)
            # The send mail method only trigger when actually any changes
            # b/w the previous, current instance's `attr` field's values and
            # if applicable for the automation
            if getattr(instance_value, "pk", None) and isinstance(
                instance_value, models.Model
            ):
                instance_value = str(getattr(instance_value, "pk", None))
                previous_instance_value = str(
                    getattr(previous_instance_value, "pk", None)
                )
            elif isinstance(instance_value, QuerySet):
                instance_value = list(instance_value.values_list("pk", flat=True))
                previous_instance_value = list(
                    previous_instance_value.values_list("pk", flat=True)
                )

            instance_values.append(instance_value)

            previous_instance_values.append(previous_instance_value)

            if not condition.get("logic"):

                applicable = evaluate_condition(instance_value, operator, value)
            logic = condition.get("logic")
            if logic:
                applicable = operator_map[logic](
                    applicable,
                    evaluate_condition(instance_value, operator, value),
                )
            if not applicable:
                false_exists = True
            if logic == "and":
                and_exists = True
            if false_exists and and_exists:
                applicable = False
                break
    if applicable:
        if created and automation.trigger == "on_create":
            send_mail(request, automation, instance)
        elif (automation.trigger == "on_update") and (
            set(previous_instance_values) != set(instance_values)
        ):

            send_mail(request, automation, instance)


def send_mail(request, automation, instance):
    """
    mail sending method
    """
    from horilla_views.templatetags.generic_template_filters import getattribute
    from horilla_automations.methods.methods import (
        get_model_class,
        get_related_field_model,
    )
    from base.methods import generate_pdf
    from base.backends import ConfiguredEmailBackend
    from horilla.decorators import logger

    mail_template = automation.mail_template
    pk = getattribute(instance, automation.mail_details)
    model_class = get_model_class(automation.model)
    model_class = get_related_field_model(model_class, automation.mail_details)
    mail_to_instance = model_class.objects.filter(pk=pk).first()
    tos = []
    for mapping in eval(automation.mail_to):
        tos.append(getattribute(mail_to_instance, mapping))
    to = tos[:1]
    cc = tos[1:]
    email_backend = ConfiguredEmailBackend()
    host = email_backend.dynamic_username
    if mail_to_instance and request:
        attachments = []
        try:
            sender = request.user.employee_get
        except:
            sender = None
        for template_attachment in automation.template_attachments.all():
            template_bdy = template.Template(template_attachment.body)
            context = template.Context({"instance": mail_to_instance, "self": sender})
            render_bdy = template_bdy.render(context)
            attachments.append(
                (
                    "Document",
                    generate_pdf(render_bdy, {}, path=False, title="Document").content,
                    "application/pdf",
                )
            )

        template_bdy = template.Template(mail_template.body)
        context = template.Context({"instance": mail_to_instance, "self": sender})
        render_bdy = template_bdy.render(context)
        email = EmailMessage(automation.title, render_bdy, host, to=to, cc=cc)
        email.content_subtype = "html"

        email.attachments = attachments

        def _send_mail(email):
            try:
                email.send()
            except Exception as e:
                logger.error(e)

        thread = threading.Thread(
            target=lambda: _send_mail(email),
        )
        thread.start()
