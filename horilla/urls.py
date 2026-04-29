"""horilla URL Configuration

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

from . import settings
from .external_views import (
    contracts_view,
    payroll_app_view,
    hiring_view,
    all_messages_view,
    candidate_inbox_notifications,
    candidate_inbox_unread_count,
)


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path("contracts/", contracts_view, name="contracts-embed"),
    path("payroll-app/", payroll_app_view, name="payroll-app-embed"),
    path("hiring-portal/", hiring_view, name="hiring-portal-embed"),
    path("all-messages/", all_messages_view, name="all-messages-embed"),
    path("api/candidate-inbox/notifications/", candidate_inbox_notifications, name="candidate-inbox-notifications"),
    path("api/candidate-inbox/unread-count/", candidate_inbox_unread_count, name="candidate-inbox-unread-count"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("base.urls")),
    path("", include("horilla_automations.urls")),
    path("", include("horilla_views.urls")),
    path("employee/", include("employee.urls")),
    path("horilla-widget/", include("horilla_widgets.urls")),
    path("api/", include("horilla_api.urls")),
    re_path(
        "^inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", health_check),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
