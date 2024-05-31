"""
This module extends the Django settings related to templates to include a
custom context processor for biometric functionality.
It imports the `TEMPLATES` setting from `horilla.settings` and appends a
custom context processor path to it.
"""

from horilla.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "biometric.context_processors.biometric_is_installed",
)
