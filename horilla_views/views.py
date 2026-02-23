import csv
import importlib
import json
import os
import re
from collections import defaultdict
from io import BytesIO

from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.staticfiles import finders
from django.core.cache import cache as CACHE
from django.core.exceptions import FieldDoesNotExist
from django.db import connection, router
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from xhtml2pdf import pisa

from base.methods import eval_validate
from horilla.decorators import login_required as func_login_required
from horilla.signals import post_generic_delete, pre_generic_delete
from horilla_views import models
from horilla_views.cbv_methods import (
    get_nested_field,
    get_short_uuid,
    login_required,
    merge_dicts,
    set_nested_attr,
)
from horilla_views.forms import SavedFilterForm
from horilla_views.generic.cbv.views import HorillaFormView, HorillaListView
from horilla_views.templatetags.generic_template_filters import getattribute

# Create your views here.


reshaper = ArabicReshaper(
    {
        "support_ligatures": False,
    }
)


@method_decorator(login_required, name="dispatch")
class ToggleColumn(View):
    """
    ToggleColumn
    """

    def get(self, *args, **kwargs):
        """
        method to toggle columns
        """

        query_dict = self.request.GET
        path = query_dict["path"]
        query_dict = dict(query_dict)
        del query_dict["path"]

        hidden_fields = [key for key, value in query_dict.items() if value[0]]

        existing_instance = models.ToggleColumn.objects.filter(
            user_id=self.request.user, path=path
        ).first()

        instance = models.ToggleColumn() if not existing_instance else existing_instance
        instance.path = path
        instance.excluded_columns = hidden_fields

        instance.save()

        return HttpResponse("success")


@method_decorator(login_required, name="dispatch")
class ReloadField(View):
    """
    ReloadField
    """

    def get(self, request, *args, **kwargs):
        """
        Http method to reload dynamic create fields
        """
        class_path = request.GET["form_class_path"]
        reload_field = request.GET["dynamic_field"]

        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        parent_form = getattr(module, class_name)()

        dynamic_cache = CACHE.get(request.session.session_key + "cbv" + reload_field)
        onchange = CACHE.get(
            request.session.session_key + "cbv" + reload_field + "onchange"
        )
        if not onchange:
            onchange = ""

        model: models.HorillaModel = dynamic_cache["model"]
        value = dynamic_cache.get("value", "")

        cache_field = dynamic_cache["dynamic_field"]
        if cache_field != reload_field:
            cache_field = reload_field
        field = parent_form.fields[cache_field]

        queryset = model.objects.all()
        queryset = field.queryset
        choices = [(instance.id, instance) for instance in queryset]
        choices.insert(0, ("", "Select option"))
        choices.append(("dynamic_create", "Dynamic create"))

        form_field = forms.ChoiceField
        if isinstance(field, forms.ModelMultipleChoiceField):
            form_field = forms.MultipleChoiceField
            dynamic_initial = request.GET.get("dynamic_initial", [])
            value = eval_validate(f"""[{dynamic_cache["value"]},{dynamic_initial}]""")
        else:
            if not value and self.request.GET.get("dynamic_initial"):
                value = eval_validate(self.request.GET.get("dynamic_initial"))

        parent_form.fields[cache_field] = form_field(
            choices=choices,
            label=field.label,
            required=field.required,
        )
        parent_form.fields[cache_field].widget.option_template_name = (
            "horilla_widgets/select_option.html",
        )
        parent_form.fields[cache_field].widget.attrs = field.widget.attrs
        parent_form.fields[cache_field].initial = value
        parent_form.fields[cache_field].widget.attrs["onchange"] = onchange

        field = parent_form[cache_field]
        dynamic_id: str = get_short_uuid(4)
        return render(
            request,
            "generic/reload_select_field.html",
            {"field": field, "dynamic_id": dynamic_id},
        )


@method_decorator(login_required, name="dispatch")
class ActiveTab(View):
    def get(self, *args, **kwargs):
        """
        CBV method to handle active tab
        """
        path = self.request.GET.get("path")
        target = self.request.GET.get("target")
        if path and target and self.request.user:
            existing_instance = models.ActiveTab.objects.filter(
                created_by=self.request.user, path=path
            ).first()

            instance = (
                models.ActiveTab() if not existing_instance else existing_instance
            )
            instance.path = path
            instance.tab_target = target
            instance.save()
        return JsonResponse({"message": "Success"})


@method_decorator(login_required, name="dispatch")
class ActiveGroup(View):
    def get(self, *args, **kwargs):
        """
        ActiveGroup
        """
        path = self.request.GET.get("path")
        target = self.request.GET.get("target")
        group_field = self.request.GET.get("field")
        if path and target and group_field and self.request.user:
            existing_instance = models.ActiveGroup.objects.filter(
                created_by=self.request.user,
                path=path,
                group_by_field=group_field,
            ).first()

            instance = (
                models.ActiveGroup() if not existing_instance else existing_instance
            )
            instance.path = path
            instance.group_by_field = group_field
            instance.group_target = target
            instance.save()
        return JsonResponse({"message": "Success"})


@method_decorator(login_required, name="dispatch")
class SavedFilter(HorillaFormView):
    """
    SavedFilter
    """

    model = models.SavedFilter
    form_class = SavedFilterForm
    new_display_title = "Save Applied Filter"
    template_name = "generic/saved_filter_form.html"
    form_disaply_attr = "Blah"

    def form_valid(self, form: SavedFilterForm) -> HttpResponse:
        referrer = self.request.POST.get("referrer", "")
        path = self.request.POST.get("path", "/")
        result_dict = {key: value[0] for key, value in self.request.GET.lists()}
        if form.is_valid():
            instance: models.SavedFilter = form.save(commit=False)
            if not instance.pk:
                instance.path = path
                instance.referrer = referrer
                instance.filter = result_dict
                instance.urlencode = self.request.GET.urlencode()
            instance.save()
            messages.success(self.request, "Filter Saved")
            return self.HttpResponse()
        return super().form_valid(form)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        referrer = self.request.GET.get("referrer", "")
        if referrer:
            # Remove the protocol and domain part
            referrer = "/" + "/".join(referrer.split("/")[3:])
        context["path"] = self.request.GET.get("path", "")
        context["referrer"] = referrer
        return context


@method_decorator(login_required, name="dispatch")
class DeleteSavedFilter(View):
    """
    Delete saved filter
    """

    def get(self, *args, **kwargs):
        pk = kwargs["pk"]
        models.SavedFilter.objects.filter(created_by=self.request.user, pk=pk).delete()
        return HttpResponse("")


@method_decorator(login_required, name="dispatch")
class ActiveView(View):
    """
    ActiveView CBV
    """

    def get(self, *args, **kwargs):
        path = self.request.GET["path"]
        view_type = self.request.GET["view"]
        active_view = models.ActiveView.objects.filter(
            path=path, created_by=self.request.user
        ).first()

        active_view = active_view if active_view else models.ActiveView()
        active_view.path = path
        active_view.type = view_type
        active_view.save()
        return HttpResponse("")


@method_decorator(login_required, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class SearchInIds(View):
    """
    Search in ids view
    """

    def get(self, *args, **kwargs):
        """
        Search in instance ids method
        """
        cache_key = f"{self.request.session.session_key}search_in_instance_ids"
        context: dict = CACHE.get(cache_key)
        if context:
            context["instances"] = context["filter_class"](self.request.GET).qs
        return render(self.request, "generic/filter_result.html", context)


@method_decorator(login_required, name="dispatch")
class LastAppliedFilter(View):
    """
    Class view to handle last applied filter
    """

    def get(self, *args, **kwargs):
        """
        Get method
        """

        nav_path = self.request.GET.get(
            "nav_url",
        )
        if nav_path:
            CACHE.set(
                self.request.session.session_key + "last-applied-filter" + nav_path,
                self.request.GET,
                timeout=600,
            )
        return HttpResponse("success")


@method_decorator(login_required, name="dispatch")
class DynamiListView(HorillaListView):
    """
    DynamicListView for Generic Delete
    """

    instances = []

    def get_queryset(self):
        search = self.request.GET.get("search", "")

        def _search_filter(instance):
            return search in str(instance).lower()

        return filter(_search_filter, self.instances)


@method_decorator(login_required, name="dispatch")
class HorillaDeleteConfirmationView(View):
    """
    Generic Delete Confirmation View
    """

    confirmation_target = "deleteConfirmationBody"

    def get(self, *args, **kwargs):
        """
        GET method
        """
        from horilla.urls import path, urlpatterns

        pk = self.request.GET.get("pk")
        try:
            app, MODEL_NAME = self.request.GET.get("model").split(".")
        except:
            messages.error(self.request, "Invalid model parameter format.")
            return HorillaFormView.HttpResponse()

        if not self.request.user.has_perm(app + ".delete_" + MODEL_NAME.lower()):
            return render(self.request, "no_perm.html")
        model = apps.get_model(app, MODEL_NAME)

        delete_object = model.objects.get(pk=pk)
        objs = [delete_object]
        using = router.db_for_write(delete_object._meta.model)
        collector = NestedObjects(using=using, origin=objs)
        collector.collect(objs)
        MODEL_MAP = {}
        PROTECTED_MODEL_MAP = {}
        DYNAMIC_PATH_MAP = {}
        MODEL_RELATED_FIELD_MAP = {}
        MODEL_RELATED_PROTECTED_FIELD_MAP = {}

        def format_callback(instance, protected=False):
            if not MODEL_RELATED_FIELD_MAP.get(instance._meta.model):
                MODEL_RELATED_FIELD_MAP[instance._meta.model] = []
                MODEL_RELATED_PROTECTED_FIELD_MAP[instance._meta.model] = []

            def find_related_field(obj, related_instance):
                for field in obj._meta.get_fields():
                    # Check if the field is a foreign key (or related model)
                    if isinstance(
                        field, (models.models.ForeignKey, models.models.OneToOneField)
                    ):
                        # Get the field value
                        field_value = getattr(obj, field.name)
                        # If the field value matches the related instance, return the field name
                        if field_value == related_instance:
                            if "PROTECT" in field.remote_field.on_delete.__name__:
                                MODEL_RELATED_PROTECTED_FIELD_MAP[
                                    instance._meta.model
                                ].append((field.name, field.verbose_name))
                            MODEL_RELATED_FIELD_MAP[instance._meta.model].append(
                                field.name
                            )

            find_related_field(instance, delete_object)
            app_label = instance._meta.app_label
            app_label = apps.get_app_config(app_label).verbose_name
            model = instance._meta.model

            model.verbose_name = model.__name__.split("_")[0]

            model_map = PROTECTED_MODEL_MAP if protected else MODEL_MAP

            if app_label not in model_map:
                model_map[app_label] = {}

            if model not in model_map[app_label]:
                model_map[app_label][model] = []
                DYNAMIC_PATH_MAP[model.verbose_name] = (
                    f"{get_short_uuid(prefix='generic-delete',length=10)}"
                )

                class DynamiListView(HorillaListView):
                    """
                    DynamicListView for Generic Delete
                    """

                    instances = []
                    columns = [
                        (
                            "Record",
                            "dynamic_display_name_generic_delete",
                        ),
                    ]
                    records_per_page = 5
                    filter_selected = False
                    quick_export = False

                    selected_instances_key_id = "storedIds" + app_label

                    def dynamic_display_name_generic_delete(self):

                        is_protected = False
                        classname = self.__class__.__name__
                        app_label = self._meta.app_label

                        app_verbose_name = apps.get_app_config(app_label).verbose_name
                        protected = PROTECTED_MODEL_MAP.get(app_verbose_name, {}).get(
                            self._meta.model, []
                        )
                        ids = [instance.pk for instance in protected]
                        if self.pk in ids:
                            is_protected = True

                        if "_" in classname:
                            field_name = classname.split("_", 1)[1]
                            classname = classname.split("_")[0]

                            object_field_name = classname.lower()
                            model = apps.get_model(app_label, classname)

                            field = model._meta.get_field(field_name)

                            return f"""
                            {getattr(self, object_field_name)}
                            <i style="color:#989898;">(In {field.verbose_name})</i>
                            """
                        indication = f"""
                        {self}
                        """
                        if is_protected:
                            verbose_names = [
                                str(i[1])
                                for i in list(
                                    set(
                                        MODEL_RELATED_PROTECTED_FIELD_MAP.get(
                                            self._meta.model, ""
                                        )
                                    )
                                )
                            ]
                            indication = (
                                indication
                                + f"""
                            <i style="color:red;">(Record in {",".join(verbose_names)})</i>
                            """
                            )
                        return indication

                    def __init__(self, **kwargs):
                        super().__init__(**kwargs)
                        self._saved_filters = self.request.GET

                    def get_context_data(self, **kwargs):
                        context = super().get_context_data(**kwargs)
                        context["search_url"] = "/" + self.search_url
                        return context

                    def get_queryset(self):
                        search = self.request.GET.get("search", "")

                        def _search_filter(instance):
                            return search in str(instance).lower()

                        self.instances = list(
                            set(
                                (
                                    self.instances
                                    + MODEL_MAP.get(
                                        apps.get_app_config(
                                            self.model._meta.app_label
                                        ).verbose_name,
                                        {},
                                    ).get(self.model, [])
                                    + PROTECTED_MODEL_MAP.get(
                                        apps.get_app_config(
                                            self.model._meta.app_label
                                        ).verbose_name,
                                        {},
                                    ).get(self.model, [])
                                )
                            )
                        )

                        queryset = self.model.objects.filter(
                            pk__in=[
                                instance.pk
                                for instance in filter(_search_filter, self.instances)
                            ]
                        )
                        return queryset

                model.dynamic_display_name_generic_delete = (
                    DynamiListView.dynamic_display_name_generic_delete
                )

                DynamiListView.model = model
                if "_" in model.__name__:
                    DynamiListView.bulk_update_fields = [MODEL_NAME.lower()]
                else:
                    DynamiListView.bulk_update_fields = MODEL_RELATED_FIELD_MAP.get(
                        model, []
                    )
                DynamiListView.instances = model_map[app_label][model]
                DynamiListView.search_url = DYNAMIC_PATH_MAP[model.verbose_name]
                DynamiListView.selected_instances_key_id = (
                    DynamiListView.selected_instances_key_id + model.verbose_name
                )

                urlpatterns.append(
                    path(
                        DynamiListView.search_url,
                        DynamiListView.as_view(),
                        name=DynamiListView.search_url,
                    )
                )
            model_map[app_label][model].append(instance)

            return instance

        _to_delete = collector.nested(format_callback)
        protected = [
            format_callback(obj, protected=True) for obj in collector.protected
        ]

        model_count = {
            model._meta.verbose_name_plural: len(objs)
            for model, objs in collector.model_objs.items()
        }

        protected_model_count = defaultdict(int)

        for obj in collector.protected:
            model = type(obj)
            protected_model_count[model._meta.verbose_name_plural] += 1
        protected_model_count = dict(protected_model_count)
        context = {
            "model_map": merge_dicts(MODEL_MAP, PROTECTED_MODEL_MAP),
            "dynamic_list_path": DYNAMIC_PATH_MAP,
            "delete_object": delete_object,
            "protected": protected,
            "model_count_sum": sum(model_count.values()),
            "related_objects_count": model_count,
            "protected_objects_count": protected_model_count,
        }
        for key, value in self.get_context_data().items():
            context[key] = value

        return render(self.request, "generic/delete_confirmation.html", context)

    def post(self, *args, **kwargs):
        """
        Post method to handle the delete
        """
        pk = self.request.GET["pk"]
        app, MODEL_NAME = self.request.GET["model"].split(".")
        if not self.request.user.has_perm(app + ".delete_" + MODEL_NAME.lower()):
            return render(self.request, "no_perm.html")
        model = apps.get_model(app, MODEL_NAME)
        delete_object = model.objects.get(pk=pk)
        objs = [delete_object]
        using = router.db_for_write(delete_object._meta.model)
        collector = NestedObjects(using=using, origin=objs)
        collector.collect(objs)

        def delete_callback(instance, protected=False):
            try:
                if self.request.user.has_perm(
                    f"{instance._meta.app_label}.delete_{instance._meta.model.__name__.lower()}"
                ):
                    pre_generic_delete.send(
                        sender=instance._meta.model,
                        instance=instance,
                        args=args,
                        view_instance=self,
                        kwargs=kwargs,
                    )
                    instance.delete()
                    post_generic_delete.send(
                        sender=instance._meta.model,
                        instance=instance,
                        args=args,
                        view_instance=self,
                        kwargs=kwargs,
                    )
                    messages.success(self.request, f"Deleted {instance}")
                else:
                    messages.info(
                        self.request, f"You don't have permission to delete {instance}"
                    )
            except:
                messages.error(self.request, f"Cannot delete : {instance}")

        # deleting protected objects
        for obj in collector.protected:
            delete_callback(obj, protected=True)
        # deleting related objects
        collector.nested(delete_callback)

        return HorillaFormView.HttpResponse()

    def get_context_data(self, **kwargs) -> dict:
        context = {}
        context["confirmation_target"] = self.confirmation_target
        return context


@func_login_required
def update_kanban_sequence(request):
    """
    generic method to update the 'sequence' in kanban view.

    GET params:
    - model: 'app_label.ModelName'
    - order: list of IDs (in the desired order)
    - groupKey: optional grouping field (e.g., stage_id)
    - groupId: optional value of the grouping field
    """

    model_path = request.GET.get("model", "")
    order = request.GET.get("order", "[]")
    group_key = request.GET.get("groupKey")
    group_id = request.GET.get("groupId")
    order_by = request.GET.get("orderBy")
    order_list = json.loads(order)

    if not model_path:
        return JsonResponse({"error": "Missing 'model'."}, status=400)
    if not order_list:
        return JsonResponse({"error": "Missing 'order'."}, status=400)
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
    except Exception:
        return JsonResponse({"error": "Invalid model path."}, status=400)

    if not get_nested_field(model, order_by):
        return JsonResponse({"info": f"Model does not have a {order_by} field."})

    filters = {}
    if group_key and group_id:
        if not get_nested_field(model, group_key):
            return JsonResponse(
                {"error": f"Model does not have field '{group_key}'."}, status=400
            )

        field = get_nested_field(model, group_key)
        if field.is_relation:
            try:
                group_instance = field.related_model.objects.get(pk=group_id)
            except field.related_model.DoesNotExist:
                return JsonResponse(
                    {
                        "error": f"{field.related_model.__name__} with ID {group_id} not found."
                    },
                    status=404,
                )
            filters[group_key] = group_instance
        else:
            filters[group_key] = group_id

    objs = list(model.objects.filter(id__in=order_list, **filters))
    obj_by_id = {str(obj.id): obj for obj in objs}

    updated_objs = []
    for index, obj_id in enumerate(order_list):
        obj = obj_by_id.get(str(obj_id))
        if obj:
            set_nested_attr(obj, order_by, index)
            updated_objs.append(obj)

    if updated_objs and "__" not in order_by:
        model.objects.bulk_update(updated_objs, [order_by])

    return JsonResponse({"status": "success", "updated": len(updated_objs)})


@func_login_required
def update_kanban_item_group(request):
    """
    Generic method to update sequence and group kanban objects.

    GET parameters:
    - model: 'app_label.ModelName'
    - groupKey: foreign key field on the model (can be nested: 'stage__stage_id')
    - groupId: ID of the new group to assign
    - objectId: ID of the object being moved
    - order: ordered list of IDs to update sequence
    """

    model_path = request.GET["model"]
    group_key = request.GET.get("groupKey")
    group_id = request.GET.get("groupId")
    object_id = request.GET.get("objectId")
    order = request.GET.get("order")
    order_by = request.GET.get("orderBy")
    order_list = json.loads(order)

    if not all([model_path, group_key, group_id, object_id, order_list]):
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    try:
        model = apps.get_model(*model_path.split("."))

        # Get the group object from group_key
        group_field = get_nested_field(model, group_key)
        if hasattr(group_field, "related_model") and group_field.related_model:
            group_model = group_field.related_model
            group_instance = group_model.objects.get(id=group_id)
        else:
            # Not a ForeignKey → probably a CharField (choices) or something similar
            group_instance = group_id

        # Fetch all objects in order_list
        objects = list(model.objects.filter(id__in=order_list))
        obj_map = {str(obj.id): obj for obj in objects}
        updated = []
        fields = set()

        for index, obj_id in enumerate(order_list):
            obj = obj_map.get(str(obj_id))
            if not obj:
                continue

            set_nested_attr(obj, order_by, index)

            # If group_key is nested, set it properly
            if "__" in group_key:
                set_nested_attr(obj, group_key, group_instance)
            else:
                setattr(obj, group_key, group_instance)

            updated.append(obj)

        if "__" not in group_key:
            fields.add(group_key)

        if fields:
            model.objects.bulk_update(updated, list(fields))

        return JsonResponse({"status": "success", "updated": len(updated)})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@func_login_required
def update_kanban_group_sequence(request):
    """
    Generic method to update the sequence of kanban groups.
    """
    model_path = request.GET["model"]
    group_key = request.GET.get("group_key")
    sequence_raw = request.GET.get("sequence", "")
    order_by = request.GET.get("orderBy")

    try:
        sequence = json.loads(sequence_raw)
    except json.JSONDecodeError:
        sequence = []

    model = apps.get_model(*model_path.split("."))
    group_field = get_nested_field(model, group_key)

    group_model = group_field.related_model

    to_update = []
    for index, group_id in enumerate(sequence):
        instance = group_model(
            pk=group_id,
            sequence=index,
        )
        to_update.append(instance)

    group_model.objects.bulk_update(to_update, fields=[order_by])

    return JsonResponse(
        {"status": "success", "message": "Group sequence updated successfully."}
    )


@func_login_required
def get_kanban_card_count(request):
    """
    Generic method to get the count of kanban cards in each group.
    """
    model_path = request.GET["model"]
    group_id = request.GET.get("group_id")
    group_key = request.GET.get("group_key")

    model = apps.get_model(*model_path.split("."))
    count = model.objects.filter(**{group_key: group_id}).count()

    return HttpResponse(f"{count}")


_getattibute = getattribute


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\[\]]+', "_", filename)[:200]  # limit to 200 chars


def get_model_class(model_path):
    """
    method to return the model class from string 'app.models.Model'
    """
    module_name, class_name = model_path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    model_class = getattr(module, class_name)
    return model_class


def link_callback(uri, rel):
    """
    Convert html URIs to absolute system paths so xhtml2pdf can access them.
    Called by pisa.CreatePDF(..., link_callback=link_callback)
    """
    # If absolute URL (http/https/file) return as-is
    if (
        uri.startswith("http://")
        or uri.startswith("https://")
        or uri.startswith("file://")
    ):
        return uri

    # Try static files first
    static_path = None
    if uri.startswith(settings.STATIC_URL):
        # remove STATIC_URL prefix
        rel_path = uri.replace(settings.STATIC_URL, "")
        # find with staticfiles finders
        found = finders.find(rel_path)
        if found:
            static_path = found

    # Try media files next
    media_path = None
    if uri.startswith(settings.MEDIA_URL):
        rel_path = uri.replace(settings.MEDIA_URL, "")
        media_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    # If a path found, return it
    for path in (static_path, media_path, uri):
        if path and os.path.exists(path):
            return path

    # Last resort: maybe it's relative to your project root
    project_path = os.path.join(settings.BASE_DIR, uri)
    if os.path.exists(project_path):
        return project_path

    raise Exception("File not found for URI: %s" % uri)


def reshape_text(text):
    """
    Make text safe for xhtml2pdf:
    - Reshape Arabic
    - Apply bidi ordering
    - Leave all other languages untouched
    """

    if not isinstance(text, str):
        return text
    try:
        reshaped = reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


@func_login_required
def export_data(request, *args, **kwargs):

    # =====================================================
    # INPUT
    # =====================================================
    ids = eval_validate(request.POST.get("ids", "[]"))
    columns = eval_validate(request.POST.get("columns", "[]"))

    export_format = request.POST.get("format", "csv").lower()
    file_name = request.POST.get("export_file_name", "quick_export")

    date_range = request.session.get("report_date_range", "")

    # =====================================================
    # COMPANY
    # =====================================================
    company_name = "All Company"
    logo_path = None

    company = getattr(request, "selected_company_instance", None)
    if company:
        company_name = company.company or company_name
        if company.icon:
            logo_path = company.icon.path

    # =====================================================
    # MODEL
    # =====================================================
    model_path = request.GET.get("model")
    app_label = model_path.split(".")[0]
    model_name = model_path.split(".")[-1]
    model = apps.get_model(app_label, model_name)
    base_table = model._meta.db_table

    # =====================================================
    # SQL BUILD
    # =====================================================
    headers = []
    select_sql = [f"{base_table}.id"]
    method_columns = {}
    select_index = 1

    for label, field in columns:
        headers.append(label)

        if not field:
            select_sql.append("''")
            select_index += 1
            continue

        parts = field.split("__")

        if len(parts) == 1:
            try:
                f = model._meta.get_field(parts[0])
                if isinstance(f, (ForeignKey, OneToOneField)):
                    select_sql.append(f"{base_table}.id")
                    method_columns[select_index] = parts[0]
                else:
                    select_sql.append(f"{base_table}.{f.column}")
            except FieldDoesNotExist:
                select_sql.append(f"{base_table}.id")
                method_columns[select_index] = parts[0]

            select_index += 1
            continue

        select_sql.append(f"{base_table}.id")
        method_columns[select_index] = field
        select_index += 1

    # =====================================================
    # EXECUTE SQL
    # =====================================================
    if not ids:
        return HttpResponse("No IDs provided")

    placeholders = ", ".join(["%s"] * len(ids))

    query = f"""
        SELECT {", ".join(select_sql)}
        FROM {base_table}
        WHERE {base_table}.id IN ({placeholders})
    """

    with connection.cursor() as cursor:
        cursor.execute(query, ids)
        rows = cursor.fetchall()

    # =====================================================
    # ORM CACHE
    # =====================================================
    objs = {o.id: o for o in model.objects.filter(id__in=ids)}

    method_maps = {}
    for idx, attr in method_columns.items():
        method_maps[idx] = {}
        for obj_id, obj in objs.items():
            value = obj
            for part in attr.split("__"):
                if value is None:
                    break
                value = getattr(value, part, None)
                if callable(value):
                    value = value()
            method_maps[idx][obj_id] = str(value) if value is not None else ""

    # =====================================================
    # FINAL ROWS
    # =====================================================
    final_rows = []

    for row in rows:
        row = list(row)
        obj_id = row[0]
        for idx, mmap in method_maps.items():
            row[idx] = mmap.get(obj_id, "")
        final_rows.append(row[1:])

    # =====================================================
    # XLSX EXPORT (FIXED WIDTH – PERFORMANCE SAFE)
    # =====================================================
    if export_format == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Quick Export"

        total_columns = len(headers)
        center = Alignment(horizontal="center", vertical="center")
        header_fill = PatternFill(start_color="FFD700", fill_type="solid")
        header_font = Font(bold=True)
        thin = Side(style="thin")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # Logo
        if logo_path and os.path.exists(logo_path):
            img = Image(logo_path)
            img.width = 120
            img.height = 60
            ws.add_image(img, "A1")

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columns)
        ws.cell(row=1, column=1).value = company_name
        ws.cell(row=1, column=1).font = Font(size=14, bold=True)
        ws.cell(row=1, column=1).alignment = center

        ws.merge_cells(start_row=2, start_column=1, end_row=3, end_column=total_columns)
        ws.cell(row=2, column=1).value = file_name
        ws.cell(row=2, column=1).font = Font(size=14, bold=True, color="FF0000")
        ws.cell(row=2, column=1).alignment = center

        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=total_columns)
        ws.cell(row=4, column=1).value = date_range
        ws.cell(row=4, column=1).alignment = center

        HEADER_ROW = 5

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=HEADER_ROW, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = center

            # ✅ FIXED WIDTH (NO PERFORMANCE HIT)
            ws.column_dimensions[cell.column_letter].width = 25

        for r_idx, row in enumerate(final_rows, start=HEADER_ROW + 1):
            for c_idx, val in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx).value = val

        buf = BytesIO()
        wb.save(buf)

        response = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}.xlsx"'
        return response

    # =====================================================
    # PDF EXPORT
    # =====================================================
    if export_format == "pdf":

        html = render_to_string(
            "generic/export_pdf.html",
            {
                "headers": headers,
                "rows": [dict(zip(headers, r)) for r in final_rows],
                "company_name": company_name,
                "date_range": date_range,
                "report_title": file_name,
                "logo_path": (
                    logo_path if logo_path and os.path.exists(logo_path) else None
                ),
                "landscape": len(headers) > 5,
            },
        )

        buf = BytesIO()
        pisa.CreatePDF(html, dest=buf)

        return HttpResponse(
            buf.getvalue(),
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}.pdf"'},
        )

    # =====================================================
    # CSV EXPORT
    # =====================================================
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{file_name}.csv"'

    writer = csv.writer(response)
    writer.writerow([company_name])
    writer.writerow([file_name])
    writer.writerow([date_range])
    writer.writerow([])
    writer.writerow(headers)
    writer.writerows(final_rows)

    return response


@method_decorator(login_required, name="dispatch")
class DynamicView(View):
    """
    DynamicView
    """

    def get(self, request, *args, **kwargs):

        field = kwargs.get("field")
        session_key = kwargs.get("session_key")
        if session_key != request.session.session_key:
            return HttpResponseForbidden("Invalid session key.")

        return render(request, "dynamic.html", {"field": field})
