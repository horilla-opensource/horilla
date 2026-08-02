"""
horilla/inherit/model_inherit.py

HorillaModelBase — metaclass for HorillaModel that enables field and method
injection into existing models via _inherit = "app_label.ModelName".

Usage in an extension app:

    from horilla.models import HorillaModel

    class AssetExtension(HorillaModel):
        _inherit = "asset.Asset"

        warranty_expiry_date = models.DateField(null=True, blank=True)
        warranty_provider = models.CharField(max_length=100, blank=True)

        def clean(self):
            if self.warranty_expiry_date and self.warranty_expiry_date < date.today():
                raise ValidationError(_("Warranty has already expired."))

This returns a placeholder, not a real model — no table, no migration in the
target app. Fields appear on the target model and their migrations are routed
to the extension app via INJECTION_MAP + HorillaAutodetector.
"""

import warnings

from django.apps import apps as django_apps
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from horilla.inherit.extension_registry import INJECTION_MAP

# Global registry: {"app_label.ModelName": [{"class_name": ..., "fields": ..., "methods": ...}]}
EXTENSION_REGISTRY: dict = {}

_SKIP_KEYS = frozenset({"_inherit", "__module__", "__qualname__", "__doc__", "Meta"})


class HorillaModelBase(ModelBase):
    """
    Metaclass for HorillaModel.

    When a subclass declares `_inherit = "app_label.ModelName"`, this metaclass:
      1. Extracts all Field instances and non-dunder methods from the class body.
      2. Contributes those fields to the target model via contribute_to_class.
      3. Contributes methods to the target model, chaining clean() safely.
      4. Returns a lightweight placeholder — no new DB table, no migration state.

    All other subclasses (no _inherit) pass through to Django's standard ModelBase.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        inherit = namespace.get("_inherit")

        if inherit:
            parts = inherit.rsplit(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"_inherit must be 'app_label.ModelName', got: {inherit!r}"
                )
            app_label, model_name = parts

            contributed_fields = {
                k: v for k, v in namespace.items() if isinstance(v, models.Field)
            }

            # Injected fields must be nullable or have a default.
            # If the extension app is later removed from INSTALLED_APPS the column
            # stays in the DB (intentional — data is preserved), but Django will no
            # longer include the field in INSERT statements.  A NOT NULL / no-default
            # column will cause every new save to fail with a DB constraint error.
            for field_name, field in contributed_fields.items():
                if not field.null and field.default is models.NOT_PROVIDED:
                    warnings.warn(
                        f"{name}.{field_name}: injected field has no null=True and no default. "
                        f"If '{namespace.get('__module__', '').split('.')[0]}' is ever removed "
                        f"from INSTALLED_APPS, new {inherit} saves will fail because the "
                        f"NOT NULL column will no longer be included in INSERT statements. "
                        f"Add null=True or default=... to this field.",
                        stacklevel=2,
                    )

            contributed_methods = {
                k: v
                for k, v in namespace.items()
                if callable(v) and not k.startswith("__") and k not in _SKIP_KEYS
            }

            EXTENSION_REGISTRY.setdefault(inherit, []).append(
                {
                    "class_name": name,
                    "module": namespace.get("__module__", ""),
                    "fields": contributed_fields,
                    "methods": contributed_methods,
                }
            )

            def _apply(
                target_model,
                _fields=dict(contributed_fields),
                _methods=dict(contributed_methods),
                _extension_app=namespace.get("__module__", "").split(".")[0],
            ):
                for field_name, field in _fields.items():
                    if not hasattr(target_model, field_name):
                        field.contribute_to_class(target_model, field_name)
                        key = (
                            target_model._meta.app_label,
                            target_model._meta.model_name,
                            field_name,
                        )
                        INJECTION_MAP[key] = _extension_app

                for method_name, method in _methods.items():
                    if method_name == "clean":
                        existing = getattr(target_model, "clean", None)
                        if existing:

                            def _chained(self, _orig=existing, _ext=method):
                                _orig(self)
                                _ext(self)

                            target_model.clean = _chained
                        else:
                            target_model.clean = method
                    else:
                        if not hasattr(target_model, method_name):
                            setattr(target_model, method_name, method)

            django_apps.lazy_model_operation(_apply, (app_label, model_name))

            return type(
                name,
                (object,),
                {
                    "_is_horilla_extension": True,
                    "_inherit": inherit,
                    "_extension_fields": contributed_fields,
                    "__module__": namespace.get("__module__", ""),
                    "__qualname__": namespace.get("__qualname__", name),
                },
            )

        return super().__new__(mcs, name, bases, namespace, **kwargs)
