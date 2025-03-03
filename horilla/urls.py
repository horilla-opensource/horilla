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

import os
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

import notifications.urls

from . import settings


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path('accounts/', include("allauth.urls")),
    path("", include("base.urls")),
    path("", include("horilla_automations.urls")),
    path("", include("horilla_views.urls")),
    path("employee/", include("employee.urls")),
    path("horilla-widget/", include("horilla_widgets.urls")),
    re_path(
        "^inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", health_check),
]

if eval(os.getenv('ADMIN_ENABLED', True)):
    urlpatterns.insert(0, path("admin/", admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
