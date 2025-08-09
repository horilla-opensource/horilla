import importlib
import json
from collections import defaultdict

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.core.cache import cache as CACHE
from django.db import router
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from base.methods import eval_validate
from horilla.signals import post_generic_delete, pre_generic_delete
from horilla_views import models
from horilla_views.cbv_methods import get_short_uuid, login_required, merge_dicts
from horilla_views.forms import SavedFilterForm
from horilla_views.generic.cbv.views import HorillaFormView, HorillaListView

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

    if not model_path:
        return JsonResponse({"error": "Missing 'model' or 'order'."}, status=400)
    if not order_list:
        return JsonResponse({})
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
    except Exception:
        return JsonResponse({"error": "Invalid model path."}, status=400)

    if "sequence" not in [f.name for f in model._meta.fields]:
        return JsonResponse({"info": "Model does not have a 'sequence' field."})

    filters = {}
    if group_key and group_id:
        if not hasattr(model, group_key):
            return JsonResponse(
                {"error": f"Model does not have field '{group_key}'."}, status=400
            )

        field = model._meta.get_field(group_key)
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
            obj.sequence = index
            updated_objs.append(obj)

    if updated_objs:
        model.objects.bulk_update(updated_objs, ["sequence"])

    return JsonResponse({"status": "success", "updated": len(updated_objs)})


def update_kanban_item_group(request):
    """
    Generic method to update sequence and group kanban objects.

    GET parameters:
    - model: 'app_label.ModelName'
    - groupKey: foreign key field on the model (e.g., 'stage_id')
    - groupId: ID of the new group to assign
    - objectId: ID of the object being moved
    - order: ordered list of IDs to update sequence
    """

    model_path = request.GET.get("model")
    group_key = request.GET.get("groupKey")
    group_id = request.GET.get("groupId")
    object_id = request.GET.get("objectId")
    order = request.GET.get("order")
    order_list = json.loads(order)

    if not all([model_path, group_key, group_id, object_id, order_list]):
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    try:
        model = apps.get_model(*model_path.split("."))
        group_field = model._meta.get_field(group_key)
        group_model = group_field.related_model
        group_instance = group_model.objects.get(id=group_id)

        # Get all objects that match order_list
        objects = list(model.objects.filter(id__in=order_list))
        obj_map = {str(obj.id): obj for obj in objects}
        updated = []
        fields = []

        for index, obj_id in enumerate(order_list):
            obj = obj_map.get(str(obj_id))
            if not obj:
                continue
            if hasattr(obj, "sequence"):
                fields.append("sequence")
                setattr(obj, "sequence", index)

            setattr(obj, group_key, group_instance)

            # Special logic for "hired" if needed
            if (
                group_key == "stage_id"
                and hasattr(obj, "hired")
                and hasattr(group_instance, "stage_type")
            ):
                obj.hired = group_instance.stage_type == "hired"

            updated.append(obj)

        fields.append(group_key)
        if any(hasattr(o, "hired") for o in updated):
            fields.append("hired")

        model.objects.bulk_update(updated, fields)

        return JsonResponse({"status": "success", "updated": len(updated)})
    except Exception as e:
        return JsonResponse({"error": f"{e}"}, status=500)


def update_kanban_group_sequence(request):
    """
    Generic method to update the sequence of kanban groups.
    """
    model_path = request.GET.get("model")
    group_key = request.GET.get("group_key")
    sequence_raw = request.GET.get("sequence", "")
    try:
        sequence = json.loads(sequence_raw)
    except json.JSONDecodeError:
        sequence = []

    model = apps.get_model(*model_path.split("."))
    group_field = model._meta.get_field(group_key)
    group_model = group_field.related_model

    to_update = []
    for index, group_id in enumerate(sequence):
        instance = group_model(
            pk=group_id,
            sequence=index,
        )
        to_update.append(instance)

    group_model.objects.bulk_update(to_update, fields=["sequence"])

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
