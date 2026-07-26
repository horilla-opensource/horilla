"""
Client-specific overrides.

Imported last from horilla.settings.__init__ (after base + addons).
Override settings here; do NOT use ``from .base import *`` — that re-exports
base MEDIA_* values and wipes AWS S3 paths set by addons.py.

Examples:

    DEBUG = False
    ALLOWED_HOSTS = ["client.example.com"]
    WHITE_LABELLING = True
    DOC_BASE_URL = "https://www.horilla.com"

    # Extend lists via selective import (same list object as base):
    from .base import INSTALLED_APPS, MIDDLEWARE

    INSTALLED_APPS += ["client_portal"]
    MIDDLEWARE += ["client_portal.middleware.ClientTrackingMiddleware"]
"""
