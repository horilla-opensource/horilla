"""
horilla/config.py

Horilla app configurations
"""

import os, importlib, logging
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from horilla.horilla_apps import SIDEBARS

logger = logging.getLogger(__name__)


def get_apps_in_base_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir_apps = []

    for app_name in settings.INSTALLED_APPS:
        app_module = __import__(app_name)
        app_path = os.path.dirname(os.path.abspath(app_module.__file__))
        if app_path.startswith(base_dir):
            base_dir_apps.append(app_name)

    return SIDEBARS


def import_method(accessibility):
    module_path, method_name = accessibility.rsplit(".", 1)
    module = __import__(module_path, fromlist=[method_name])
    accessibility_method = getattr(module, method_name)
    return accessibility_method


ALL_MENUS = {}


def sidebar(request):

    base_dir_apps = get_apps_in_base_dir()

    if not request.user.is_anonymous:
        request.MENUS = []
        MENUS = request.MENUS

        for app in base_dir_apps:

            try:
                sidebar = importlib.import_module(app + ".sidebar")

            except Exception as e:
                logger.error(e)
                continue

            if sidebar:
                accessibility = None
                if getattr(sidebar, "ACCESSIBILITY", None):
                    accessibility = import_method(sidebar.ACCESSIBILITY)

                if not accessibility or accessibility(
                    request,
                    sidebar.MENU,
                    PermWrapper(request.user),
                ):
                    MENU = {}
                    MENU["menu"] = sidebar.MENU
                    MENU["app"] = app
                    MENU["img_src"] = sidebar.IMG_SRC
                    MENU["submenu"] = []
                    MENUS.append(MENU)
                    for submenu in sidebar.SUBMENUS:

                        accessibility = None

                        if submenu.get("accessibility"):
                            accessibility = import_method(submenu["accessibility"])

                        if not accessibility or accessibility(
                            request,
                            submenu,
                            PermWrapper(request.user),
                        ):
                            MENU["submenu"].append(submenu)
        ALL_MENUS[request.session.session_key] = MENUS


def get_MENUS(request):
    ALL_MENUS[request.session.session_key] = []
    sidebar(request)
    return {"sidebar": ALL_MENUS.get(request.session.session_key)}
