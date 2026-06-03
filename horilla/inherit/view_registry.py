"""
horilla/inherit/view_registry.py

Registry for the two _inherit modes supported by HorillaViewInheritMixin.

Mode 1 — _inherit = True  (direct-subclass replacement)
  register_replacement() patches parent_cls.__new__ so every instantiation
  of the parent (including existing URL closures) transparently creates an
  instance of the extension class instead.

Mode 2 — _inherit = "app_label.ClassName"  (indirect attribute injection)
  The target view must be registered via register_view(). Declared attributes
  are applied to the target via setattr. Use this to avoid circular imports.
"""

from __future__ import annotations

# "app_label.ClassName" → active view class
VIEW_REGISTRY: dict = {}

# Mode-2 pending contributions  "app_label.ClassName" → [{"extension_app", "contributions"}]
VIEW_EXTENSION_REGISTRY: dict = {}


# ---------------------------------------------------------------------------
# Registration helpers
# ---------------------------------------------------------------------------


def register_view(key: str, view_cls) -> None:
    """
    Register a view class as a Mode-2 target.
    Applies any pending attribute contributions registered before this view was imported.
    """
    VIEW_REGISTRY[key] = view_cls

    for ext in VIEW_EXTENSION_REGISTRY.get(key, []):
        _apply_contributions(view_cls, ext["contributions"])


def register_replacement(parent_cls, ext_cls) -> None:
    """
    Mode-1 registration: ext_cls replaces parent_cls via __new__ patching.
    Called immediately when the extension class is defined (via HorillaViewInheritMixin).
    """
    _patch_new(parent_cls, ext_cls)


def register_extension(key: str, extension_app: str, contributions: dict) -> None:
    """
    Mode-2 registration: applies a dict of attributes to the named view.
    If the target view is already registered, applies immediately.
    """
    VIEW_EXTENSION_REGISTRY.setdefault(key, []).append(
        {"extension_app": extension_app, "contributions": contributions}
    )
    if key in VIEW_REGISTRY:
        _apply_contributions(VIEW_REGISTRY[key], contributions)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _patch_new(parent_cls, ext_cls) -> None:
    """
    Override parent_cls.__new__ so that parent_cls() returns an ext_cls instance.

    When the existing URL closure instantiates parent_cls:
      1. type.__call__(parent_cls, **kwargs)
      2. parent_cls.__new__(parent_cls) → our override → object.__new__(ext_cls)
      3. isinstance(ext_instance, parent_cls) == True  (ext_cls is a subclass)
      4. type.__call__ calls ext_instance.__init__(**kwargs)  ✓

    The `cls is parent_cls` guard lets super().__new__() calls from ext_cls
    fall through normally without infinite recursion.
    """

    @staticmethod
    def __new__(cls, *args, **kwargs):
        return object.__new__(ext_cls if cls is parent_cls else cls)

    parent_cls.__new__ = __new__


def _apply_contributions(view_cls, contributions: dict) -> None:
    """Mode-2: set each contributed attribute directly on the view class."""
    for attr, value in contributions.items():
        setattr(view_cls, attr, value)
