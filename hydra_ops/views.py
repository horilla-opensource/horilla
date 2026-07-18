from django.http import JsonResponse
from django.views.decorators.http import require_GET

from hydra_ops.readiness import collect_readiness


@require_GET
def readiness_check(request):
    # A high-frequency orchestration probe must stay bounded. The full domain
    # audit remains part of release readiness and explicit operator checks.
    results = collect_readiness(
        include_filesystem=False,
        include_migrations=False,
        include_domain_integrity=False,
    )
    ready = all(result.ok for result in results)
    response = JsonResponse({"status": "ready" if ready else "not_ready"}, status=200 if ready else 503)
    response["Cache-Control"] = "no-store"
    return response
