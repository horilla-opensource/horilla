import importlib

from django import forms
from django.contrib import messages
from django.core.cache import cache as CACHE
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from horilla_views import models
from horilla_views.cbv_methods import get_short_uuid, login_required
from horilla_views.forms import SavedFilterForm
from horilla_views.generic.cbv.views import HorillaFormView

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
        model: models.HorillaModel = dynamic_cache["model"]

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

        parent_form.fields[cache_field] = form_field(
            choices=choices,
            label=field.label,
            required=field.required,
        )
        dynamic_initial = request.GET.get("dynamic_initial", [])
        parent_form.fields[cache_field].widget.attrs = field.widget.attrs
        parent_form.fields[cache_field].initial = eval(
            f"""[{dynamic_cache["value"]},{dynamic_initial}]"""
        )

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
        CACHE.set(
            self.request.session.session_key + "last-applied-filter",
            self.request.GET,
            timeout=600,
        )
        return HttpResponse("success")
