"""
Custom Swagger settings for the API
"""

from django.conf import settings

# Define security definitions for Swagger UI
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": 'JWT Token Authentication: Enter your token with the "Bearer " prefix, e.g. "Bearer abcde12345"',
        }
    },
    "USE_SESSION_AUTH": False,
    "DEFAULT_UI_SETTINGS": {
        # Keep tag order as defined in the generated spec
        "tagsSorter": "none"
    },
    "SECURITY_REQUIREMENTS": [{"Bearer": []}],
}

# Apply settings
if hasattr(settings, "SWAGGER_SETTINGS"):
    settings.SWAGGER_SETTINGS.update(SWAGGER_SETTINGS)
else:
    setattr(settings, "SWAGGER_SETTINGS", SWAGGER_SETTINGS)
