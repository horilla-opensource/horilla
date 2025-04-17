from django.contrib import messages
from django.http import HttpResponseRedirect

from horilla.horilla_middlewares import _thread_locals
from project.methods import (
    any_project_manager,
    any_project_member,
    any_task_manager,
    any_task_member,
    has_subordinates,
)

# from project.sidebar import has_subordinates


decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def is_projectmanager_or_member_or_perms(function, perm):
    def _function(self, *args, **kwargs):
        """
        This method is used to check the employee is project manager or not
        """
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        if (
            user.has_perm(perm)
            or any_project_manager(user)
            or any_project_member(user)
            or any_task_manager(user)
            or any_task_member(user)
        ):
            return function(self, *args, **kwargs)
        messages.info(request, "You don't have permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return _function
