"""
horilla/cbv_methods.py
"""

from urllib.parse import urlencode
import uuid
from venv import logger
from django import template
from django.shortcuts import redirect, render
from django.template import loader
from django.template.loader import render_to_string
from django.template.defaultfilters import register
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.middleware.csrf import get_token
from django.utils.html import format_html
from django.utils.functional import lazy
from django.utils.safestring import SafeString

from horilla import settings
from horilla_views.templatetags.generic_template_filters import getattribute
from base.thread_local_middleware import _thread_locals


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
    request = context["request"]
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
    if cache.get(request.session.session_key):
        cache[request.session.session_key].update({view: {}})
        return
    cache.update({request.session.session_key: {view: {}}})
    return


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


class Reverse:
    reverse: bool = True
    page: str = ""


cache = {}


def sortby(
    query_dict, queryset, key: str, page: str = "page", is_first_sort: bool = False
):
    """
    New simplified method to sort the queryset/lists
    """
    request = getattr(_thread_locals, "request", None)
    sort_key = query_dict[key]
    if not cache.get(request.session.session_key):
        cache[request.session.session_key] = Reverse()
        cache[request.session.session_key].page = (
            "1" if not query_dict.get(page) else query_dict.get(page)
        )
    reverse = cache[request.session.session_key].reverse
    none_ids = []

    def _sortby(object):
        result = getattribute(object, attr=sort_key)
        if result is None:
            none_ids.append(object.pk)
        return result

    order = not reverse
    current_page = query_dict.get(page)
    if current_page or is_first_sort:
        order = not order
        if (
            cache[request.session.session_key].page == current_page
            and not is_first_sort
        ):
            order = not order
        cache[request.session.session_key].page = current_page
    try:
        queryset = sorted(queryset, key=_sortby, reverse=order)
    except TypeError:
        none_queryset = list(queryset.filter(id__in=none_ids))
        queryset = sorted(queryset.exclude(id__in=none_ids), key=_sortby, reverse=order)
        queryset = queryset + none_queryset

    cache[request.session.session_key].reverse = order
    order = "asc" if not order else "desc"
    setattr(request, "sort_order", order)
    setattr(request, "sort_key", sort_key)
    return queryset


def update_saved_filter_cache(request, cache):
    """
    Method to save filter on cache
    """
    if cache.get(request.session.session_key):
        cache[request.session.session_key].update(
            {
                "path": request.path,
                "query_dict": request.GET,
                "request": request,
            }
        )
        return cache
    cache.update(
        {
            request.session.session_key: {
                "path": request.path,
                "query_dict": request.GET,
                "request": request,
            }
        }
    )
    return cache
