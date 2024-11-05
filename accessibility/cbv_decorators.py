"""
employee/decorators.py
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from accessibility.methods import check_is_accessible
from base.decorators import decorator_with_arguments
from horilla.horilla_middlewares import _thread_locals


@decorator_with_arguments
def enter_if_accessible(function, feature, perm=None, method=None):
    """
    accessible check decorator for cbv
    """

    def check_accessible(self, *args, **kwargs):
        """
        Check accessible
        """
        path = "/"
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
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

        if accessible or has_perm or method(request):
            return function(self, *args, **kwargs)
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
