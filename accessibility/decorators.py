"""
employee/decorators.py
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from accessibility.methods import check_is_accessible
from base.decorators import decorator_with_arguments


@decorator_with_arguments
def enter_if_accessible(function, feature, perm=None, method=None):
    """
    accessiblie check decorator
    """

    def check_accessible(request, *args, **kwargs):
        """
        Check accessible
        """
        path = "/"
        referrer = request.META.get("HTTP_REFERER")
        if referrer and request.path not in referrer:
            path = request.META["HTTP_REFERER"]
        accessible = False
        cache_key = request.session.session_key + "accessibility_filter"
        employee = getattr(request.user, "employee_get")
        if employee:
            accessible = check_is_accessible(feature, cache_key, employee)
        has_perm = True
        if perm:
            has_perm = request.user.has_perm(perm)

        if accessible or has_perm or (method and method(request, *args, **kwargs)):
            return function(request, *args, **kwargs)
        key = "HTTP_HX_REQUEST"
        keys = request.META.keys()
        messages.info(request, _("You dont have access to the feature"))
        if key in keys:
            return HttpResponse(
                f"""
                <script>
                window.location.href="{referrer}"
                </script>
                """
            )
        return redirect(path)

    return check_accessible
