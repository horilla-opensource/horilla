"""
horilla_apps

This module is used to register horilla addons
"""
from horilla.settings import INSTALLED_APPS
from horilla import settings

INSTALLED_APPS.append("horilla_audit")
INSTALLED_APPS.append("horilla_widgets")
INSTALLED_APPS.append("horilla_crumbs")

setattr(settings,"EMAIL_BACKEND",'base.backends.ConfiguredEmailBackend')