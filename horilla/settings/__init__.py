"""
horilla/settings/__init__.py
Combines official base settings + client overrides.
"""

from .base import *

# Import client overrides (if file exists)
try:
    from .addons import *
    from .local_settings import *
except ImportError:
    pass
