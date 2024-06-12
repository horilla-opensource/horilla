"""
horilla/generic/views.py
"""

import json
from django import forms
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import render
from django.urls import reverse
from typing import Any
from django.urls import resolve
from urllib.parse import parse_qs
from django.core.paginator import Page
from django.views.generic import ListView, DetailView, TemplateView, FormView
from attendance.methods.group_by import group_by_queryset
from base.methods import (
    closest_numbers,
    get_key_instances,
)
from horilla.filters import FilterSet
from horilla_views import models
from horilla_views.cbv_methods import (
    get_short_uuid,
    paginator_qry,
    update_initial_cache,
    sortby,
    update_saved_filter_cache,
)
from base.thread_local_middleware import _thread_locals
from horilla_views.cbv_methods import structured
from horilla_views.forms import ToggleColumnForm
from horilla_views.templatetags.generic_template_filters import getattribute


cache = {}
saved_filters = {}


class HorillaListView(ListView):
    """
    HorillaListView
    """

    filter_class: FilterSet = None

    view_id: str = """"""

    export_file_name: str = None

    template_name: str = "generic/horilla_list.html"
    context_object_name = "queryset"
    # column = [("Verbose Name","field_name","avatar_mapping")], opt: avatar_mapping
    columns: list = []
    search_url: str = ""
    bulk_select_option: bool = True

    action_method: str = """"""
    actions: list = []

    option_method: str = ""
    options: list = []
    row_attrs: str = """"""
    row_status_class: str = """"""
    row_status_indications: list = []

    sortby_key: str = "sortby"
    sortby_mapping: list = []

    show_filter_tags: bool = True
    filter_keys_to_remove: list = []

    records_per_page: int = 50

    def __init__(self, **kwargs: Any) -> None:
        self.view_id = get_short_uuid(4)
        super().__init__(**kwargs)

        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaListView)

        # hidden columns configuration
        existing_instance = models.ToggleColumn.objects.filter(
            user_id=request.user, path=request.path_info
        ).first()

        hidden_fields = (
            [] if not existing_instance else existing_instance.excluded_columns
        )

        self.visible_column = self.columns.copy()

        self.toggle_form = ToggleColumnForm(self.columns, hidden_fields)
        for column in self.columns:
            if column[1] in hidden_fields:
                self.visible_column.remove(column)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.filter_class:
            query_dict = self.request.GET
            if "filter_applied" in query_dict.keys():
                update_saved_filter_cache(self.request, saved_filters)
            elif saved_filters.get(self.request.session.session_key):
                query_dict = saved_filters[self.request.session.session_key][
                    "query_dict"
                ]

            self._saved_filters = query_dict
            queryset = self.filter_class(query_dict, queryset).qs
        return queryset

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context["view_id"] = self.view_id
        context["columns"] = self.visible_column
        context["toggle_form"] = self.toggle_form
        context["search_url"] = self.search_url

        context["action_method"] = self.action_method
        context["actions"] = self.actions

        context["option_method"] = self.option_method
        context["options"] = self.options
        context["row_attrs"] = self.row_attrs

        context["show_filter_tags"] = self.show_filter_tags
        context["bulk_select_option"] = self.bulk_select_option
        context["row_status_class"] = self.row_status_class
        context["sortby_key"] = self.sortby_key
        context["sortby_mapping"] = self.sortby_mapping
        context["row_status_indications"] = self.row_status_indications
        context["saved_filters"] = self._saved_filters

        context["select_all_ids"] = self.select_all
        if self._saved_filters.get("field"):
            active_group = models.ActiveGroup.objects.filter(
                created_by=self.request.user,
                path=self.request.path,
                group_by_field=self._saved_filters["field"],
            ).first()
            if active_group:
                context["active_target"] = active_group.group_target

        queryset = self.get_queryset()

        if self.show_filter_tags:
            data_dict = parse_qs(self._saved_filters.urlencode())
            data_dict = get_key_instances(self.model, data_dict)
            keys_to_remove = [
                key
                for key, value in data_dict.items()
                if value[0] in ["unknown", "on"] + self.filter_keys_to_remove
            ]

            for key in keys_to_remove:
                data_dict.pop(key)
            context["filter_dict"] = data_dict

        request = self.request
        ordered_ids = list(queryset.values_list("id", flat=True))
        model = queryset.model
        is_first_sort = False
        query_dict = self.request.GET
        if (
            not request.GET.get(self.sortby_key)
            and not self._saved_filters.get(self.sortby_key)
        ) or (
            not request.GET.get(self.sortby_key)
            and self._saved_filters.get(self.sortby_key)
        ):
            is_first_sort = True
            query_dict = self._saved_filters

        if query_dict.get(self.sortby_key):
            queryset = sortby(
                query_dict, queryset, self.sortby_key, is_first_sort=is_first_sort
            )
            ordered_ids = [instance.id for instance in queryset]
        setattr(model, "ordered_ids", ordered_ids)

        context["queryset"] = paginator_qry(
            queryset, self._saved_filters.get("page"), self.records_per_page
        )

        if request and self._saved_filters.get("field"):
            field = self._saved_filters.get("field")
            self.template_name = "generic/group_by.html"
            if isinstance(queryset, Page):
                queryset = self.filter_class(
                    request.GET, queryset=queryset.object_list.model.objects.all()
                ).qs
            groups = group_by_queryset(
                queryset, field, self._saved_filters.get("page"), "page"
            )
            context["groups"] = paginator_qry(
                groups, self._saved_filters.get("page"), 10
            )
        cache[self.request.session.session_key][HorillaListView] = context
        from horilla.urls import urlpatterns, path

        self.export_path = f"export-list-view-{get_short_uuid(4)}/"

        urlpatterns.append(path(self.export_path, self.export_data))
        context["export_path"] = self.export_path
        return context

    def select_all(self, *args, **kwargs):
        """
        Select all method
        """
        return json.dumps(list(self.get_queryset().values_list("id", flat=True)))

    def export_data(self, *args, **kwargs):
        """
        Export list view visible columns
        """
        from import_export import resources, fields

        request = getattr(_thread_locals, "request", None)
        ids = eval(request.GET["ids"])
        queryset = self.model.objects.filter(id__in=ids)

        MODEL = self.model
        FIELDS = self.visible_column

        class HorillaListViewResorce(resources.ModelResource):
            id = fields.Field(column_name="ID")

            class Meta:
                model = MODEL
                fields = []

            def dehydrate_id(self, instance):
                return instance.pk

            def before_export(self, queryset, *args, **kwargs):
                return super().before_export(queryset, *args, **kwargs)

            for field_tuple in FIELDS:
                dynamic_fn_str = f"def dehydrate_{field_tuple[1]}(self, instance):return str(getattribute(instance, '{field_tuple[1]}'))"
                exec(dynamic_fn_str)
                dynamic_fn = locals()[f"dehydrate_{field_tuple[1]}"]
                locals()[field_tuple[1]] = fields.Field(column_name=field_tuple[0])

        book_resource = HorillaListViewResorce()

        # Export the data using the resource
        dataset = book_resource.export(queryset)

        excel_data = dataset.export("xls")

        # Set the response headers
        file_name = self.export_file_name
        if not file_name:
            file_name = "quick_export"
        response = HttpResponse(excel_data, content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = f'attachment; filename="{file_name}.xls"'
        return response


class HorillaSectionView(TemplateView):
    """
    Horilla Template View
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaListView)

    nav_url: str = ""
    view_url: str = ""

    # view container id is used to wrap the component view with th id
    view_container_id: str = ""

    script_static_paths: list = []
    style_static_paths: list = []

    template_name = "generic/horilla_section.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["nav_url"] = self.nav_url
        context["view_url"] = self.view_url
        context["view_container_id"] = self.view_container_id
        context["script_static_paths"] = self.script_static_paths
        context["style_static_paths"] = self.style_static_paths
        return context


class HorillaDetailedView(DetailView):
    """
    HorillDetailedView
    """

    title = "Detailed View"
    template_name = "generic/horilla_detailed_view.html"
    header: dict = {"title": "Horilla", "subtitle": "Horilla Detailed View"}
    body: list = []

    action_method: list = []
    actions: list = []

    ids_key: str = "instance_ids"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaDetailedView)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)

        instance_ids = eval(str(self.request.GET.get(self.ids_key)))

        pk = context["object"].pk

        url = resolve(self.request.path)
        key = list(url.kwargs.keys())[0]

        url_name = url.url_name

        previous_id, next_id = closest_numbers(instance_ids, pk)

        next_url = reverse(url_name, kwargs={key: next_id})
        previous_url = reverse(url_name, kwargs={key: previous_id})
        if instance_ids:
            context["instance_ids"] = str(instance_ids)
            context["ids_key"] = self.ids_key

            context["next_url"] = next_url
            context["previous_url"] = previous_url

        context["title"] = self.title
        context["header"] = self.header
        context["body"] = self.body
        context["actions"] = self.actions
        context["action_method"] = self.action_method

        cache[self.request.session.session_key][HorillaDetailedView] = context

        return context


class HorillaTabView(TemplateView):
    """
    HorillaTabView
    """

    template_name = "generic/horilla_tabs.html"

    tabs: list = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaTabView)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user:
            active_tab = models.ActiveTab.objects.filter(
                created_by=self.request.user, path=self.request.path
            ).first()
            if active_tab:
                context["active_target"] = active_tab.tab_target
        context["tabs"] = self.tabs

        cache[self.request.session.session_key][HorillaTabView] = context

        return context


class HorillaCardView(ListView):
    """
    HorillaCardView
    """

    filter_class: FilterSet = None

    view_id: str = get_short_uuid(4, prefix="hcv")

    template_name = "generic/horilla_card.html"
    context_object_name = "queryset"

    search_url: str = ""

    details: dict = {}

    actions: list = []

    card_attrs: str = """"""

    show_filter_tags: bool = True
    filter_keys_to_remove: list = []

    records_per_page: int = 50
    card_status_class: str = """"""
    card_status_indications: list = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaCardView)
        self._saved_filters = QueryDict()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.filter_class:
            query_dict = self.request.GET
            if "filter_applied" in query_dict.keys():
                update_saved_filter_cache(self.request, saved_filters)
            elif saved_filters.get(self.request.session.session_key):
                query_dict = saved_filters[self.request.session.session_key][
                    "query_dict"
                ]

            self._saved_filters = query_dict
            queryset = self.filter_class(query_dict, queryset).qs
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        context["view_id"] = self.view_id
        context["search_url"] = self.search_url
        context["card_attrs"] = self.card_attrs
        context["actions"] = self.actions
        context["details"] = self.details
        context["show_filter_tags"] = self.show_filter_tags
        context["card_status_class"] = self.card_status_class
        context["card_status_indications"] = self.card_status_indications

        context["queryset"] = paginator_qry(
            queryset, self.request.GET.get("page"), self.records_per_page
        )

        if self.show_filter_tags:
            data_dict = parse_qs(self._saved_filters.urlencode())
            data_dict = get_key_instances(self.model, data_dict)
            keys_to_remove = [
                key
                for key, value in data_dict.items()
                if value[0] in ["unknown", "on"] + self.filter_keys_to_remove
            ]

            for key in keys_to_remove:
                data_dict.pop(key)
            context["filter_dict"] = data_dict

        cache[self.request.session.session_key][HorillaCardView] = context
        return context


class ReloadMessages(TemplateView):
    template_name = "generic/messages.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


dynamic_create_cache = {}


def save(self: forms.ModelForm, commit=True, *args, **kwargs):
    """
    This method is used to super save the form using custom logic
    """
    request = getattr(_thread_locals, "request", None)

    dynamic_field = request.GET["dynamic_field"]
    response = None
    if commit:
        response = super(type(self), self).save(*args, **kwargs)
        new_isntance_pk = self.instance.pk
        dynamic_create_cache[request.session.session_key + dynamic_field] = {
            "dynamic_field": dynamic_field,
            "value": new_isntance_pk,
            "form": self,
        }
    return response


from django.views.generic import UpdateView


class HorillaFormView(FormView):
    """
    HorillaFormView
    """

    class HttpResponse:
        def __new__(
            self, content: str = "", targets_to_reload: list = [], script: str = ""
        ) -> HttpResponse:
            targets_to_reload = list(set(targets_to_reload))
            targets_to_reload.append("#reloadMessagesButton")
            script_id = get_short_uuid(4)
            script = (
                f"<script id='scriptTarget{script_id}'>"
                + "{}".format(
                    "".join([f"$(`{target}`).click();" for target in targets_to_reload])
                )
                + f"$('#scriptTarget{script_id}').closest('.oh-modal--show').first().removeClass('oh-modal--show');"
                + "$('.reload-record').click();"
                + "$('.reload-field').click();"
                + script
                + "</script>"
            )

            reload_response = HttpResponse(script).content

            user_response = HttpResponse(content).content
            response = HttpResponse(reload_response + user_response)
            self = response
            return response

    model: object = None
    view_id: str = get_short_uuid(4)
    form_class: forms.ModelForm = None
    template_name = "generic/horilla_form.html"
    form_disaply_attr: str = ""
    new_display_title: str = "Add New"
    close_button_attrs: str = """"""
    submit_button_attrs: str = """"""

    # NOTE: Dynamic create view's forms save method will be overwritten
    is_dynamic_create_view: bool = False
    dynamic_create_fields: list = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaFormView)

        if self.form_class:
            setattr(self.form_class, "structured", structured)

    def get(
        self, request: HttpRequest, pk=None, *args: str, **kwargs: Any
    ) -> HttpResponse:
        response = super().get(request, *args, **kwargs)
        return response

    def post(
        self, request: HttpRequest, pk=None, *args: str, **kwargs: Any
    ) -> HttpResponse:
        self.get_form()
        response = super().post(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["dynamic_create_fields"] = self.dynamic_create_fields
        context["form_class_path"] = self.form_class_path
        context["view_id"] = self.view_id
        return context

    def get_form(self, form_class=None):
        pk = self.kwargs.get("pk")
        instance = self.model.objects.filter(pk=pk).first()

        data = None
        files = None
        if self.request.method == "POST":
            data = self.request.POST
            files = self.request.FILES
        form = self.form_class(data, files, instance=instance)

        if self.is_dynamic_create_view:
            setattr(type(form), "save", save)

        self.form_class_path = form.__class__.__module__ + "." + form.__class__.__name__
        if self.request.method == "GET":
            for dynamic_tuple in self.dynamic_create_fields:
                view = dynamic_tuple[1]
                view.display_title = "Dynamic create"

                field = dynamic_tuple[0]
                dynamic_create_cache[self.request.session.session_key + field] = {
                    "dynamic_field": field,
                    "value": getattr(form.instance, field, ""),
                    "form": form,
                }

                from horilla.urls import urlpatterns, path

                urlpatterns.append(
                    path(
                        f"dynamic-path-{field}-{self.request.session.session_key}",
                        view.as_view(),
                        name=f"dynamic-path-{field}-{self.request.session.session_key}",
                    )
                )
                queryset = form.fields[field].queryset
                choices = [(instance.id, instance) for instance in queryset]
                choices.insert(0, ("", "Select option"))
                choices.append(("dynamic_create", "Dynamic create"))
                form.fields[field] = forms.ChoiceField(
                    choices=choices,
                    label=form.fields[field].label,
                    required=form.fields[field].required,
                    widget=forms.Select(attrs=form.fields[field].widget.attrs),
                )
        if pk:
            form.instance = instance
            title = str(instance)
            if self.form_disaply_attr:
                title = getattribute(instance, self.form_disaply_attr)
            if instance:
                self.form_class.verbose_name = title
        else:
            self.form_class.verbose_name = self.new_display_title
        form.close_button_attrs = self.close_button_attrs
        form.submit_button_attrs = self.submit_button_attrs
        cache[self.request.session.session_key][HorillaFormView] = form
        self.form = form
        return form


class HorillaNavView(TemplateView):
    """
    HorillaNavView

    filter form submit button id: applyFilter
    """

    template_name = "generic/horilla_nav.html"

    nav_title: str = ""
    search_url: str = ""
    search_swap_target: str = ""
    search_input_attrs: str = ""
    search_in: list = []
    actions: list = []
    group_by_fields: list = []
    filter_form_context_name: str = ""
    filter_instance: FilterSet = None
    filter_instance_context_name: str = ""
    filter_body_template: str = ""
    view_types: list = []
    create_attrs: str = """"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        update_initial_cache(request, cache, HorillaNavView)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_title"] = self.nav_title
        context["search_url"] = self.search_url
        context["search_swap_target"] = self.search_swap_target
        context["search_input_attrs"] = self.search_input_attrs
        context["group_by_fields"] = self.group_by_fields
        context["actions"] = self.actions
        context["filter_body_template"] = self.filter_body_template
        context["view_types"] = self.view_types
        context["create_attrs"] = self.create_attrs
        context["search_in"] = self.search_in
        context["filter_instance_context_name"] = self.filter_instance
        if self.filter_instance:
            context[self.filter_form_context_name] = self.filter_instance.form
        cache[self.request.session.session_key][HorillaNavView] = context
        return context
