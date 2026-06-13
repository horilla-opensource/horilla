"""
Settings sidebar menu registry.

Apps register their settings sections with::

    from horilla.menu import settings_menu
    from attendance.sidebar import hour_account_accessibility

    @settings_menu.register
    class MyAppSettings:
        title = _("My App")
        icon  = "/static/assets/icons/my-app.svg"
        order = 3
        items = [
            {
                "label":         _("Config"),
                "url":           reverse_lazy("my_app:config"),
                "hx-target":     "#settingsContainer",
                "hx-push-url":   "true",
                "hx-select":     "#my-app-config-view",
                "hx-select-oob": "#settings-sidebar",
                "accessibility": hour_account_accessibility,
            },
        ]

The ``accessibility`` value can be:
  - a callable with signature ``fn(request, submenu, user_perms, *args, **kwargs) -> bool``
  - a plain bool (``True`` / ``False``)
  - omitted — defaults to ``True`` (item always visible)
"""

from django.contrib.auth.context_processors import PermWrapper

from horilla.menu.registry import MenuRegistry


class SettingsRegistry(MenuRegistry):
    """
    Registry for Settings-page sidebar sections.

    Each registered class must define:
      - title  (str | lazy str)
      - icon   (str — static path)
      - items  (list[dict])

    And optionally:
      - order      (int)
      - condition  (bool | callable(request) -> bool)

    Each item dict supports:
      - label, url, hx-target, hx-push-url, hx-select, hx-select-oob  (required)
      - accessibility  (dotted import string — if omitted, defaults to True)
      - order          (int, optional)
    """

    # ------------------------------------------------------------------
    # Item-level visibility
    # ------------------------------------------------------------------

    @staticmethod
    def _item_visible(item, request):
        """
        Evaluate the item's accessibility value.
        - callable  → called with (request, item, user_perms), must return bool
        - bool      → used directly
        - absent    → True (visible by default)
        """
        accessibility = item.get("accessibility", True)
        if callable(accessibility):
            return bool(accessibility(request, item, PermWrapper(request.user)))
        return bool(accessibility)

    # ------------------------------------------------------------------
    # Item-level sort key (three-bucket strategy)
    # ------------------------------------------------------------------

    @staticmethod
    def _item_sort_key(item):
        order = item.get("order", None)
        if order is None:
            return (1, 0)
        if order >= 0:
            return (0, order)
        return (2, order)

    # ------------------------------------------------------------------
    # Build one section dict
    # ------------------------------------------------------------------

    def _build_entry(self, obj, request):
        raw_items = getattr(obj, "items", [])

        visible_items = [
            item for item in raw_items if self._item_visible(item, request)
        ]

        # Hide the entire section when the user has no visible items
        if not visible_items:
            return None

        visible_items = sorted(visible_items, key=self._item_sort_key)

        return {
            "title": getattr(obj, "title", ""),
            "icon": getattr(obj, "icon", ""),
            "items": visible_items,
        }


# Module-level singleton — imported by app menu.py files
settings_registry = SettingsRegistry()


def get_settings_menu(request):
    """
    Return the filtered, sorted settings sidebar menu for *request*.
    Called from SettingsView.get_context_data.
    """
    return settings_registry.get_entries(request)
