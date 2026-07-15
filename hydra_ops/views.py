from django.http import JsonResponse
from django.views.decorators.http import require_GET

from hydra_ops.readiness import collect_readiness


@require_GET
def readiness_check(request):
    results = collect_readiness(include_filesystem=False, include_migrations=True)
    ready = all(result.ok for result in results)
    response = JsonResponse({"status": "ready" if ready else "not_ready"}, status=200 if ready else 503)
    response["Cache-Control"] = "no-store"
    return response
