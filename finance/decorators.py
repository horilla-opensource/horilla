from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from project.models import Project  
def finance_update_required():
    """Decorator to check if the user has permission to edit finance details."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, project_id, *args, **kwargs):
            project = get_object_or_404(Project, id=project_id)
            if not request.user.has_perm("finance.change_finance") and not request.user.is_superuser:
                messages.info(request, "You don't have access to edit this project's finance.")
                return redirect("finance_project_list")  
            return view_func(request, project_id, *args, **kwargs)
        return _wrapped_view
    return decorator

def finance_view_required():
    """Decorator to check if the user has permission to view finance details."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, project_id, *args, **kwargs):
            project = get_object_or_404(Project, id=project_id)
            if not request.user.has_perm("finance.view_finance") and not request.user.is_superuser:
                messages.info(request, "You don't have access to view this project's finance.")
                return redirect("finance_project_list") 
            return view_func(request, project_id, *args, **kwargs)
        return _wrapped_view
    return decorator
 
def profit_distribution_required():
    """Decorator to check if the user has permission to view and edit profit distribution."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, project_id, *args, **kwargs):
            project = get_object_or_404(Project, id=project_id)
            if not request.user.has_perm("finance.change_profitdistribution") and not request.user.is_superuser:
                messages.info(request, "You don't have access to modify the profit distribution for this project.")
                return redirect("finance_dashboard", project_id=project_id)  
            return view_func(request, project_id, *args, **kwargs)
        return _wrapped_view
    return decorator

def project_finance_list():
    """Decorator to check if the user has permission to view finance details."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm("finance.view_finance") and not request.user.is_superuser:
                messages.info(request, "You don't have access to view this project's finance.")
                return redirect("home-page")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
