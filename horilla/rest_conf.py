"""
rest_conf.py
"""

from datetime import timedelta

from horilla import settings
from horilla.settings import INSTALLED_APPS

# Injecting installed apps to settings

REST_APPS = ["rest_framework", "rest_framework_simplejwt", "drf_yasg", "horilla_api"]

INSTALLED_APPS.extend(REST_APPS)

REST_FRAMEWORK_SETTINGS = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
}
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter your Bearer token here",
        },
        "Basic": {
            "type": "basic",
            "description": "Basic authentication. Enter your username and password.",
        },
    },
    "SECURITY": [{"Bearer": []}, {"Basic": []}],
}
# Inject the REST framework settings into the Django project settings
setattr(settings, "REST_FRAMEWORK", REST_FRAMEWORK_SETTINGS)
setattr(settings, "SIMPLE_JWT", SIMPLE_JWT)
setattr(settings, "SWAGGER_SETTINGS", SWAGGER_SETTINGS)
