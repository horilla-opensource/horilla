import importlib
import io
import json
import re
from collections import defaultdict

from bs4 import BeautifulSoup
from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.core.cache import cache as CACHE
from django.db import router
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from import_export import fields, resources
from xhtml2pdf import pisa

from base.methods import eval_validate
from horilla.decorators import login_required as func_login_required
from horilla.horilla_middlewares import _thread_locals
from horilla.signals import post_generic_delete, pre_generic_delete
from horilla_views import models
from horilla_views.cbv_methods import (
    export_xlsx,
    get_nested_field,
    get_short_uuid,
    login_required,
    merge_dicts,
    render_to_string,
    set_nested_attr,
)
from horilla_views.forms import SavedFilterForm
from horilla_views.generic.cbv.views import HorillaFormView, HorillaListView
from horilla_views.templatetags.generic_template_filters import getattribute

# Create your views here.


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
    order = request.GET.get("order")
    group_key = request.GET.get("groupKey")
    group_id = request.GET.get("groupId")
    order_list = json.loads(order)
    order_by = request.GET.get("orderBy")

    if not model_path:
        return JsonResponse({"error": "Missing 'model' or 'order'."}, status=400)
    if not order_list:
        return JsonResponse({})
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

    model_path = request.GET.get("model")
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


def update_kanban_group_sequence(request):
    """
    Generic method to update the sequence of kanban groups.
    """
    model_path = request.GET.get("model")
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


def get_kanban_card_count(request):
    """
    Generic method to get the count of kanban cards in each group.
    """
    model_path = request.GET.get("model")
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


import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static


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


@func_login_required
def export_data(request, *args, **kwargs):
    """
    Export list view visible columns
    """
    from horilla_views.generic.cbv.views import HorillaFormView

    request = getattr(_thread_locals, "request", None)
    ids = eval_validate(request.POST["ids"])
    _columns = eval_validate(request.POST["columns"])
    export_format = request.POST.get("format", "xlsx")

    model: models.models.Model = get_model_class(model_path=request.GET["model"])

    if not request.user.has_perm(
        f"""{request.GET["model"].split(".")[0]}.view_{model.__name__}"""
    ):
        messages.info(f"You dont have view perm for model {model._meta.verbose_name}")
        return HorillaFormView.HttpResponse()
    queryset = model.objects.filter(id__in=ids)
    export_fields = eval_validate(request.POST["export_fields"])
    export_file_name = request.POST["export_file_name"]
    export_file_name = sanitize_filename(export_file_name)

    _model = model

    class HorillaListViewResorce(resources.ModelResource):
        """
        Instant Resource class
        """

        id = fields.Field(column_name="ID")

        class Meta:
            """
            Meta class for additional option
            """

            model = _model
            fields = [field[1] for field in _columns]  # 773

        def dehydrate_id(self, instance):
            """
            Dehydrate method for id field
            """
            return instance.pk

        for field_tuple in _columns:
            dynamic_fn_str = f"def dehydrate_{field_tuple[1]}(self, instance):return self.remove_extra_spaces(getattribute(instance, '{field_tuple[1]}'),{field_tuple})"
            exec(dynamic_fn_str)
            dynamic_fn = locals()[f"dehydrate_{field_tuple[1]}"]
            locals()[field_tuple[1]] = fields.Field(column_name=field_tuple[0])

        def remove_extra_spaces(self, text, field_tuple):
            """
            Clean the text:
            - If it's a <select> element, extract the selected option's value.
            - If it's an <input> or <textarea>, extract its 'value'.
            - Otherwise, remove blank spaces, keep line breaks, and handle <li> tags.
            """
            soup = BeautifulSoup(str(text), "html.parser")

            # Handle <select> tag
            select_tag = soup.find("select")
            if select_tag:
                selected_option = select_tag.find("option", selected=True)
                if selected_option:
                    return selected_option["value"]
                else:
                    first_option = select_tag.find("option")
                    return first_option["value"] if first_option else ""

            # Handle <input> tag
            input_tag = soup.find("input")
            if input_tag:
                return input_tag.get("value", "")

            # Handle <textarea> tag
            textarea_tag = soup.find("textarea")
            if textarea_tag:
                return textarea_tag.text.strip()

            # Default: clean normal text and <li> handling
            for li in soup.find_all("li"):
                li.insert_before("\n")
                li.unwrap()

            text = soup.get_text()
            lines = text.splitlines()
            non_blank_lines = [line.strip() for line in lines if line.strip()]
            cleaned_text = "\n".join(non_blank_lines)
            return cleaned_text

    book_resource = HorillaListViewResorce()

    # Export the data using the resource
    dataset = book_resource.export(queryset)

    # excel_data = dataset.export("xls")

    # Set the response headers
    # file_name = self.export_file_name
    # if not file_name:
    #     file_name = "quick_export"
    # response = HttpResponse(excel_data, content_type="application/vnd.ms-excel")
    # response["Content-Disposition"] = f'attachment; filename="{file_name}.xls"'
    # return response

    json_data = json.loads(dataset.export("json"))
    merged = []

    for item in _columns:
        # Check if item has exactly 2 elements
        if len(item) == 2:
            # Check if there's a matching (type, key) in export_fields (t, k, _)
            match_found = any(
                export_item[0] == item[0] and export_item[1] == item[1]
                for export_item in export_fields
            )

            if match_found:
                # Find the first matching metadata or use {} as fallback
                try:
                    metadata = next(
                        (
                            export_item[2]
                            for export_item in export_fields
                            if export_item[0] == item[0] and export_item[1] == item[1]
                        ),
                        {},
                    )
                except Exception as e:
                    merged.append(item)
                    continue

                merged.append([*item, metadata])
            else:
                merged.append(item)
        else:
            merged.append(item)
    columns = []
    for column in merged:
        if len(column) >= 3 and isinstance(column[2], dict):
            column = (column[0], column[0], column[2])
        elif len(column) >= 3:
            column = (column[0], column[1])
        columns.append(column)

    logo_path = ""
    company_title = ""

    company = request.selected_company_instance
    if company:
        logo_path = company.icon
        company_title = company.company

    if export_format == "json":
        response = HttpResponse(
            json.dumps(json_data, indent=4), content_type="application/json"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{export_file_name}.json"'
        )
        return response
    # CSV
    elif export_format == "csv":
        csv_data = dataset.export("csv")
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{export_file_name}.csv"'
        )
        return response
    elif export_format == "pdf":

        headers = dataset.headers
        rows = dataset.dict
        if not logo_path:
            logo_path = static(os.path.join(settings.BASE_DIR, logo_path))

        # Get absolute logo path from ImageField or fallback
        if logo_path:
            # If it's a FieldFile (from ImageField), convert to string
            if hasattr(logo_path, "path"):
                abs_logo_path = logo_path.path  # full file system path
            else:
                abs_logo_path = os.path.join(settings.BASE_DIR, str(logo_path))
        else:
            abs_logo_path = None
        # Render to HTML using a template
        landscape = len(headers) > 5
        html_string = render_to_string(
            "generic/export_pdf.html",
            {
                "headers": headers,
                "rows": rows,
                "landscape": landscape,
                "company_name": company_title,
                "date_range": (
                    request.session.get("report_date_range")
                    if request.session.get("report_date_range")
                    else ""
                ),
                "report_title": export_file_name,
                "logo_path": abs_logo_path,
            },
        )

        # Convert HTML to PDF using xhtml2pdf
        result = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            html_string, dest=result, link_callback=link_callback
        )

        if pisa_status.err:
            return HttpResponse("PDF generation failed", status=500)

        # Return response
        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{export_file_name}.pdf"'
        )
        return response

    return export_xlsx(
        json_data,
        columns,
        file_name=export_file_name,
        extra_info={
            "company_name": company_title,
            "date_range": request.session.get("report_date_range"),
            "report_title": export_file_name,
            "logo_path": logo_path,
        },
    )


class DynamicView(View):
    """
    DynamicView
    """

    def get(self, request, field, session_key):
        if session_key != request.session.session_key:
            return HttpResponseForbidden("Invalid session key.")

        # Your logic here
        return render(request, "dynamic.html", {"field": field})
