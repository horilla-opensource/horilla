"""
pms/signals.py
"""
import copy
import logging
import threading
import types
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from horilla.horilla_middlewares import _thread_locals
from pms.models import BonusPointSetting
from datetime import date




SIGNAL_HANDLERS = []
INSTANCE_HANDLERS = []

def start_automation():
    """
    Automation signals
    """
    from horilla_automations.methods.methods import get_model_class, split_query_string
    

    @receiver(post_delete, sender=BonusPointSetting)
    @receiver(post_save, sender=BonusPointSetting)
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
        bonus_point_settings = BonusPointSetting.objects.filter(is_active=True)
        for bonus_point_setting in bonus_point_settings:

            # condition_querystring = bonus_point_setting.condition_querystring.replace(
            #     "automation_multiple_", ""
            # )

            # query_strings = split_query_string(condition_querystring)
            # model_path should me in the form of pms.models.Objective
            model_path = bonus_point_setting.model
            model_class = get_model_class(model_path)

            # handler = create_post_bulk_update_handler(
            #     bonus_point_setting, model_class, query_strings
            # )
            # SIGNAL_HANDLERS.append(handler)
            # post_bulk_update.connect(handler, sender=model_class)

            def create_signal_handler(name, bonus_point_setting):
                def signal_handler(sender, instance, created, **kwargs):
                    """
                    Signal handler for post-save events of the model instances.
                    """
                    # request = getattr(_thread_locals, "request", None)
                    # previous_record = getattr(_thread_locals, "previous_record", None)
                    # previous_instance = None
                    # if previous_record:
                    #     previous_instance = previous_record["instance"]
                    
                    # if BonusPointSetting.objects.filter(model='Task').exists():
                    # bonus_point_settings = BonusPointSetting.objects.filter(model='Task')
                    # for bs in bonus_point_settings:

                    field_1 = date.today()
                    field_2 = instance.end_date
                    
                    if bonus_point_setting.bonus_for == instance.status :
                        
                        for employee in instance.task_members.all():
                            bonus_point_setting.create_employee_bonus(employee,field_1,field_2)

                signal_handler.__name__ = name
                signal_handler.model_class = model_class
                signal_handler.bonus_point_setting = bonus_point_setting
                return signal_handler

            # Create and connect the signal handler
            handler_name = f"{bonus_point_setting.id}_signal_handler"
            dynamic_signal_handler = create_signal_handler(
                handler_name, bonus_point_setting
            )
            SIGNAL_HANDLERS.append(dynamic_signal_handler)
            post_save.connect(
                dynamic_signal_handler, sender=dynamic_signal_handler.model_class
            )

    def create_pre_bulk_update_handler(automation, model_class):
        def pre_bulk_update_handler(sender, queryset, *args, **kwargs):
            request = getattr(_thread_locals, "request", None)
            if request:
                queryset_copy = queryset.none()
                if queryset.count():
                    queryset_copy = QuerySet.from_list(copy.deepcopy(list(queryset)))
                _thread_locals.previous_bulk_record = {
                    "automation": automation,
                    "queryset": queryset,
                    "queryset_copy": queryset_copy,
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
        bonus_point_settings = BonusPointSetting.objects.filter(is_active=True)
        for bonus_setting in bonus_point_settings:
            model_class = get_model_class(bonus_setting.model)

            # handler = create_pre_bulk_update_handler(bonus_setting, model_class)
            # INSTANCE_HANDLERS.append(handler)
            # pre_bulk_update.connect(handler, sender=model_class)

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
                        "bonus_setting": bonus_setting,
                        "instance": instance,
                    }
                instance_handler.__name__ = (
                    f"{bonus_setting.id}_instance_handler"
                )
                return instance_handler

            instance_handler.model_class = model_class
            instance_handler.bonus_setting = bonus_setting

            INSTANCE_HANDLERS.append(instance_handler)

    track_previous_instance()
    start_connection()
