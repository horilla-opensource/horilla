from django.apps import apps
from django.http import JsonResponse

from base.methods import has_export_access
from horilla.decorators import login_required


@login_required
def check_export_access(request):
    """
    Backend enforcement point for the Reports "Export Table" action.

    Reuses the centralized ``has_export_access`` check so a user who can
    view a report but lacks export permission for its model cannot export
    it, including by calling this endpoint directly instead of through the
    "Export Table" button.
    """
    model_path = request.GET.get("model", "")
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return JsonResponse({"allowed": False})

    return JsonResponse({"allowed": has_export_access(request, model)})
