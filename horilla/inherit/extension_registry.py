"""
horilla/inherit/extension_registry.py

Lightweight registry with no Django dependencies — safe to import at any time.

INJECTION_MAP  maps (app_label, model_name_lower, field_name) to the
               extension app label so HorillaAutodetector can route AddField
               operations to the custom app's migrations instead of the
               target app's migrations.
"""

# {(app_label, model_name_lower, field_name): extension_app_label}
INJECTION_MAP: dict = {}
