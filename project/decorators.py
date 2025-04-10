from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps
from django.utils.translation import gettext_lazy as _

def delete_permission(view_func):
    """
    Decorator to check if a user has permission to delete a project.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.has_perm("project.delete_project"):
            messages.info(request, _("You don't have permission to delete this project."))
            return redirect('project:project_list')
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from functools import wraps
from django.utils.translation import gettext_lazy as _
from .models import Project 

def project_access_required(permission):
    """
    Decorator to check if a user has a specific permission (e.g., view or delete) for a project.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, pk, *args, **kwargs):
            project = get_object_or_404(Project, pk=pk)
            if not (request.user.has_perm(permission) or request.user in project.team_members.all()):
                messages.info(request, _("You don't have permission to access this project."))
                return redirect('project:project_list')

            return view_func(request, pk, *args, **kwargs)

        return _wrapped_view
    return decorator



from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from functools import wraps
from django.utils.translation import gettext_lazy as _
from .models import Project  

def project_update_required():
    """
    Decorator to check if a user has the update permission (`project.change_project`)
    or is a member of the project team.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, pk, *args, **kwargs):
            project = get_object_or_404(Project, pk=pk)
            if not (request.user.has_perm("project.change_project") or request.user in project.team_members.all()):
                messages.info(request, _("You don't have permission to update this project."))
                return redirect('project:project_list')

            return view_func(request, pk, *args, **kwargs)

        return _wrapped_view
    return decorator


from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.utils.translation import gettext_lazy as _

def project_create_required():
    """
    Decorator to check if a user has the 'project.add_project' permission before allowing project creation.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm("project.add_project"):
                messages.info(request, _("You don't have permission to create a project."))
                return redirect('project:project_list')  # Redirect to project list if unauthorized

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
