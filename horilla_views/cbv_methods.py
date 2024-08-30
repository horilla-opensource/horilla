"""
horilla/cbv_methods.py
"""

import types
import uuid
from typing import Any
from urllib.parse import urlencode
from venv import logger

from django import forms, template
from django.contrib import messages
from django.core.cache import cache as CACHE
from django.core.paginator import Paginator
from django.db import models
from django.db.models.fields.related import ForeignKey
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.template import loader
from django.template.defaultfilters import register
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _trans

from horilla import settings
from horilla.horilla_middlewares import _thread_locals
from horilla_views.templatetags.generic_template_filters import getattribute

FIELD_WIDGET_MAP = {
    models.CharField: forms.TextInput(attrs={"class": "oh-input w-100"}),
    models.ImageField: forms.FileInput(
        attrs={"type": "file", "class": "oh-input w-100"}
    ),
    models.FileField: forms.FileInput(
        attrs={"type": "file", "class": "oh-input w-100"}
    ),
    models.TextField: forms.Textarea(
        {
            "class": "oh-input w-100",
            "rows": 2,
            "cols": 40,
        }
    ),
    models.IntegerField: forms.NumberInput(attrs={"class": "oh-input w-100"}),
    models.FloatField: forms.NumberInput(attrs={"class": "oh-input w-100"}),
    models.DecimalField: forms.NumberInput(attrs={"class": "oh-input w-100"}),
    models.EmailField: forms.EmailInput(attrs={"class": "oh-input w-100"}),
    models.DateField: forms.DateInput(
        attrs={"type": "date", "class": "oh-input w-100"}
    ),
    models.DateTimeField: forms.DateTimeInput(
        attrs={"type": "date", "class": "oh-input w-100"}
    ),
    models.TimeField: forms.TimeInput(
        attrs={"type": "time", "class": "oh-input w-100"}
    ),
    models.BooleanField: forms.Select({"class": "oh-select oh-select-2 w-100"}),
    models.ForeignKey: forms.Select({"class": "oh-select oh-select-2 w-100"}),
    models.ManyToManyField: forms.SelectMultiple(
        attrs={"class": "oh-select oh-select-2 select2-hidden-accessible"}
    ),
    models.OneToOneField: forms.Select({"class": "oh-select oh-select-2 w-100"}),
}

MODEL_FORM_FIELD_MAP = {
    models.CharField: forms.CharField,
    models.TextField: forms.CharField,  # Textarea can be specified as a widget
    models.IntegerField: forms.IntegerField,
    models.FloatField: forms.FloatField,
    models.DecimalField: forms.DecimalField,
    models.ImageField: forms.FileField,
    models.FileField: forms.FileField,
    models.EmailField: forms.EmailField,
    models.DateField: forms.DateField,
    models.DateTimeField: forms.DateTimeField,
    models.TimeField: forms.TimeField,
    models.BooleanField: forms.BooleanField,
    models.ForeignKey: forms.ModelChoiceField,
    models.ManyToManyField: forms.ModelMultipleChoiceField,
    models.OneToOneField: forms.ModelChoiceField,
}


BOOLEAN_CHOICES = (
    ("", "----------"),
    (True, "Yes"),
    (False, "No"),
)


def decorator_with_arguments(decorator):
    """
    Decorator that allows decorators to accept arguments and keyword arguments.

    Args:
        decorator (function): The decorator function to be wrapped.

    Returns:
        function: The wrapper function.

    """

    def wrapper(*args, **kwargs):
        """
        Wrapper function that captures the arguments and keyword arguments.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            function: The inner wrapper function.

        """

        def inner_wrapper(func):
            """
            Inner wrapper function that applies the decorator to the function.

            Args:
                func (function): The function to be decorated.

            Returns:
                function: The decorated function.

            """
            return decorator(func, *args, **kwargs)

        return inner_wrapper

    return wrapper


def login_required(view_func):
    """
    Decorator to check authenticity of users
    """

    def wrapped_view(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        path = request.path
        res = path.split("/", 2)[1].capitalize().replace("-", " ").upper()
        if res == "PMS":
            res = "Performance"
        request.session["title"] = res
        if path == "" or path == "/":
            request.session["title"] = "Dashboard".upper()
        if not request.user.is_authenticated:
            login_url = reverse("login")
            params = urlencode(request.GET)
            url = f"{login_url}?next={request.path}"
            if params:
                url += f"&{params}"
            return redirect(url)
        try:
            func = view_func(self, request, *args, **kwargs)
        except Exception as e:
            logger.exception(e)
            if not settings.DEBUG:
                return render(request, "went_wrong.html")
            return view_func(self, *args, **kwargs)
        return func

    return wrapped_view


@decorator_with_arguments
def permission_required(function, perm):
    """
    Decorator to validate user permissions
    """

    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request

        if request.user.has_perm(perm):
            return function(self, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            return HttpResponse(script)

    return _function


@decorator_with_arguments
def check_feature_enabled(function, feature_name, model_class: models.Model):
    """
    Decorator for check feature enabled in singlton model
    """

    def _function(self, request, *args, **kwargs):
        general_setting = model_class.objects.first()
        enabled = getattr(general_setting, feature_name, False)
        if enabled:
            return function(self, request, *args, **kwargs)
        messages.info(request, _trans("Feature is not enabled on the settings"))
        previous_url = request.META.get("HTTP_REFERER", "/")
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        return HttpResponse(script)

    return _function


def hx_request_required(function):
    """
    Decorator method that only allow HTMX metod to enter
    """

    def _function(request, *args, **kwargs):
        key = "HTTP_HX_REQUEST"
        if key not in request.META.keys():
            return render(request, "405.html")
        return function(request, *args, **kwargs)

    return _function


def csrf_input(request):
    return format_html(
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">',
        get_token(request),
    )


@register.simple_tag(takes_context=True)
def csrf_token(context):
    """
    to access csrf token inside the render_template method
    """
    try:
        request = context["request"]
    except:
        request = getattr(_thread_locals, "request")
    csrf_input_lazy = lazy(csrf_input, SafeString, str)
    return csrf_input_lazy(request)


def get_all_context_variables(request) -> dict:
    """
    This method will return dictionary format of context processors
    """
    if getattr(request, "all_context_variables", None) is None:
        all_context_variables = {}
        for processor_path in settings.TEMPLATES[0]["OPTIONS"]["context_processors"]:
            module_path, func_name = processor_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[func_name])
            func = getattr(module, func_name)
            context = func(request)
            all_context_variables.update(context)
        all_context_variables["csrf_token"] = csrf_token(all_context_variables)
        request.all_context_variables = all_context_variables
    return request.all_context_variables


def render_template(
    path: str,
    context: dict,
    decoding: str = "utf-8",
    status: int = None,
    _using=None,
) -> str:
    """
    This method is used to render HTML text with context.
    """

    request = getattr(_thread_locals, "request", None)
    context.update(get_all_context_variables(request))
    template_loader = loader.get_template(path)
    template_body = template_loader.template.source
    template_bdy = template.Template(template_body)
    context_instance = template.Context(context)
    rendered_content = template_bdy.render(context_instance)
    return HttpResponse(rendered_content, status=status).content.decode(decoding)


def paginator_qry(qryset, page_number, records_per_page=50):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, records_per_page)
    qryset = paginator.get_page(page_number)
    return qryset


def get_short_uuid(length: int, prefix: str = "hlv"):
    """
    Short uuid generating method
    """
    uuid_str = str(uuid.uuid4().hex)
    return prefix + str(uuid_str[:length]).replace("-", "")


def update_initial_cache(request: object, cache: dict, view: object):

    if cache.get(request.session.session_key + "cbv"):
        cache.get(request.session.session_key + "cbv").update({view: {}})
        return
    cache.set(request.session.session_key + "cbv", {view: {}})
    return


class Reverse:
    reverse: bool = True
    page: str = ""

    def __str__(self) -> str:
        return str(self.reverse)


def getmodelattribute(value, attr: str):
    """
    Gets an attribute of a model dynamically from a string name, handling related fields.
    """
    result = value
    attrs = attr.split("__")
    for attr in attrs:
        if hasattr(result, attr):
            result = getattr(result, attr)
            if isinstance(result, ForwardManyToOneDescriptor):
                result = result.field.related_model
        elif hasattr(result, "field") and isinstance(result.field, ForeignKey):
            result = getattr(result.field.remote_field.model, attr, None)
        elif hasattr(result, "related") and isinstance(
            result, ReverseOneToOneDescriptor
        ):
            result = getattr(result.related.related_model, attr, None)
    return result


def sortby(
    query_dict, queryset, key: str, page: str = "page", is_first_sort: bool = False
):
    """
    New simplified method to sort the queryset/lists
    """
    request = getattr(_thread_locals, "request", None)
    sort_key = query_dict[key]
    if not CACHE.get(request.session.session_key + "cbvsortby"):
        CACHE.set(request.session.session_key + "cbvsortby", Reverse())
        CACHE.get(request.session.session_key + "cbvsortby").page = (
            "1" if not query_dict.get(page) else query_dict.get(page)
        )
    reverse_object = CACHE.get(request.session.session_key + "cbvsortby")
    reverse = reverse_object.reverse
    none_ids = []
    none_queryset = []
    model = queryset.model
    model_attr = getmodelattribute(model, sort_key)
    is_method = isinstance(model_attr, types.FunctionType)
    if not is_method:
        none_queryset = queryset.filter(**{f"{sort_key}__isnull": True})
        none_ids = list(none_queryset.values_list("id", flat=True))
        queryset = queryset.exclude(id__in=none_ids)

    def _sortby(object):
        result = getattribute(object, attr=sort_key)
        if result is None:
            none_ids.append(object.pk)
        return result

    order = not reverse
    current_page = query_dict.get(page)
    if current_page or is_first_sort:
        order = not order
        if reverse_object.page == current_page and not is_first_sort:
            order = not order
        reverse_object.page = current_page
    try:
        queryset = sorted(queryset, key=_sortby, reverse=order)
    except TypeError:
        none_queryset = list(queryset.filter(id__in=none_ids))
        queryset = sorted(queryset.exclude(id__in=none_ids), key=_sortby, reverse=order)

    reverse_object.reverse = order
    if order:
        order = "asc"
        queryset = list(queryset) + list(none_queryset)
    else:
        queryset = list(none_queryset) + list(queryset)
        order = "desc"
    setattr(request, "sort_order", order)
    setattr(request, "sort_key", sort_key)
    CACHE.set(request.session.session_key + "cbvsortby", reverse_object)
    return queryset


def update_saved_filter_cache(request, cache):
    """
    Method to save filter on cache
    """
    if cache.get(request.session.session_key + request.path + "cbv"):
        cache.get(request.session.session_key + request.path + "cbv").update(
            {
                "path": request.path,
                "query_dict": request.GET,
                # "request": request,
            }
        )
        return cache
    cache.set(
        request.session.session_key + request.path + "cbv",
        {
            "path": request.path,
            "query_dict": request.GET,
            # "request": request,
        },
    )
    return cache


def get_nested_field(model_class: models.Model, field_name: str) -> object:
    """
    Recursion function to execute nested field logic
    """
    if "__" in field_name:
        splits = field_name.split("__", 1)
        related_model_class = getmodelattribute(
            model_class,
            splits[0],
        ).related.related_model
        return get_nested_field(related_model_class, splits[1])
    field = getattribute(model_class, field_name)
    return field


def get_field_class_map(model_class: models.Model, bulk_update_fields: list) -> dict:
    """
    Returns a dictionary mapping field names to their corresponding field classes
    for a given model class, including related fields(one-to-one).
    """
    field_class_map = {}
    for field_name in bulk_update_fields:
        field = get_nested_field(model_class, field_name)
        field_class_map[field_name] = field.field
    return field_class_map


def structured(self):
    """
    Render the form fields as HTML table rows with Bootstrap styling.
    """
    request = getattr(_thread_locals, "request", None)
    context = {
        "form": self,
        "request": request,
    }
    table_html = render_to_string("generic/form.html", context)
    return table_html


def value_to_field(field: object, value: list) -> Any:
    """
    return value according to the format of the field
    """
    if isinstance(field, models.ManyToManyField):
        return [int(val) for val in value]
    elif isinstance(
        field,
        (
            models.DateField,
            models.DateTimeField,
            models.CharField,
            models.EmailField,
            models.TextField,
            models.TimeField,
        ),
    ):
        value = value[0]
        return value
    value = eval(str(value[0]))
    return value
