"""
horilla/inherit/view_inherit.py

HorillaViewInheritMixin — add to an extension class to enable view replacement.

Two _inherit modes
------------------

Mode 1  _inherit = True   (direct subclass replacement)
  Include HorillaViewInheritMixin as the first base alongside the target view.
  The extension replaces the parent view in URL routing via __new__ patching.
  Full Python inheritance — super(), MRO, and attribute lookup all work normally.

    from asset.cbv.asset import AssetListView
    from horilla.inherit import HorillaViewInheritMixin

    class AssetListExtension(HorillaViewInheritMixin, AssetListView):
        _inherit = True

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.columns = self.columns + ["warranty_expiry_date"]

Mode 2  _inherit = "app_label.ClassName"  (indirect attribute injection)
  No direct import of the target view needed.
  Declared non-dunder attributes are injected onto the target via setattr.
  The target view must be registered via register_view() to be reachable.

    class AssetListExtension(HorillaViewInheritMixin):
        _inherit = "asset.AssetList"
        columns = ["name", "asset_status", "warranty_expiry_date"]
"""

from horilla.inherit.view_registry import register_extension, register_replacement

_VIEW_SKIP_KEYS = frozenset(
    {
        "_inherit",
        "__module__",
        "__qualname__",
        "__doc__",
        "__classcell__",
        "Meta",
    }
)


class HorillaViewInheritMixin:
    """
    Mixin that enables _inherit on Horilla CBV extension classes.

    Include as the first base alongside the target view class.
    The target view's own metaclass is inherited from the second base,
    so there are no metaclass conflicts with Django's View machinery.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        inherit = cls.__dict__.get("_inherit")

        if inherit is True:
            parent = next(
                (b for b in cls.__bases__ if b is not HorillaViewInheritMixin),
                None,
            )
            if parent is not None:
                register_replacement(parent, cls)

        elif isinstance(inherit, str):
            parts = inherit.rsplit(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"_inherit must be 'app_label.ClassName', got: {inherit!r}"
                )
            contributions = {
                k: v
                for k, v in cls.__dict__.items()
                if not k.startswith("_") and k not in _VIEW_SKIP_KEYS
            }
            extension_app = (cls.__module__ or "").split(".")[0]
            register_extension(inherit, extension_app, contributions)
