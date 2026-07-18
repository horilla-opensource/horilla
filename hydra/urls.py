"""Hydra URL configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

import notifications.urls

from hydra_ops.views import readiness_check

from . import settings


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("base.urls")),
    path("", include("hydra_automations.urls")),
    path("", include("hydra_views.urls")),
    path("employee/", include("employee.urls")),
    path("hydra/people/", include("hydra_people.urls")),
    path("hydra/recruitment/", include("hydra_people.recruitment_urls")),
    path("hydra/documents/", include("hydra_documents.urls")),
    path("hydra/legalization/", include("hydra_legalization.urls")),
    path("hydra/imports/", include("hydra_imports.urls")),
    path("hydra/arrivals/", include("hydra_arrivals.urls")),
    path("hydra/housing/", include("hydra_housing.urls")),
    path("hydra/tasks/", include("hydra_tasks.urls")),
    path("hydra/notifications/", include("hydra_notifications.urls")),
    path("hydra/onboarding/", include("hydra_onboarding.urls")),
    path("hydra/coordination/", include("hydra_coordination.urls")),
    path("hydra/templates/", include("hydra_templates.urls")),
    path("hydra/links/", include("hydra_links.urls")),
    path("hydra/reports/", include("hydra_reports.urls")),
    path("hydra-widget/", include("hydra_widgets.urls")),
    path("api/", include("hydra_api.urls")),
    re_path(
        "^inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", health_check),
    path("health/ready/", readiness_check, name="hydra-readiness"),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
