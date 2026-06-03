"""
horilla/inherit/

Extension infrastructure for Horilla — model field injection and CBV replacement.

Key public symbols re-exported here for convenience:

    from horilla.inherit import HorillaViewInheritMixin   # view extension
    from horilla.inherit import HorillaModelBase           # model metaclass
    from horilla.inherit import INJECTION_MAP              # migration routing
    from horilla.inherit import VIEW_REGISTRY              # registered views
"""

from horilla.inherit.extension_registry import INJECTION_MAP
from horilla.inherit.model_inherit import EXTENSION_REGISTRY, HorillaModelBase
from horilla.inherit.view_inherit import HorillaViewInheritMixin
from horilla.inherit.view_registry import VIEW_REGISTRY

__all__ = [
    "HorillaViewInheritMixin",
    "HorillaModelBase",
    "INJECTION_MAP",
    "EXTENSION_REGISTRY",
    "VIEW_REGISTRY",
]
