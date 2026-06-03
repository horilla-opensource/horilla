"""
horilla/inherit/autodetect.py

Custom migration autodetector for Django 6.x.

Overrides _generate_added_field so fields registered in INJECTION_MAP
(contributed via _inherit) are routed to the extension app's migrations as
InjectField operations — not to the target app's migrations as AddField.

Django 6.x API notes (changed from 5.x):
- Field access: self.to_state.models[app_label, model_name].get_field(name)
  (previously self.new_apps.get_model(...))
- Dependencies: OperationDependency namedtuples, not (app, name) tuples
"""

from django.db.migrations.autodetector import MigrationAutodetector, OperationDependency

from horilla.inherit.extension_registry import INJECTION_MAP
from horilla.inherit.migration_ops import InjectField


class HorillaAutodetector(MigrationAutodetector):

    def _generate_added_field(self, app_label, model_name, field_name):
        key = (app_label, model_name.lower(), field_name)

        if key not in INJECTION_MAP:
            super()._generate_added_field(app_label, model_name, field_name)
            return

        ext_app = INJECTION_MAP[key]

        try:
            field = self.to_state.models[app_label, model_name.lower()].get_field(
                field_name
            )
        except Exception:
            super()._generate_added_field(app_label, model_name, field_name)
            return

        dependencies = [
            OperationDependency(
                app_label, model_name, None, OperationDependency.Type.CREATE
            ),
        ]

        self.add_operation(
            ext_app,
            InjectField(
                target_app_label=app_label,
                model_name=model_name,
                name=field_name,
                field=field,
            ),
            dependencies=dependencies,
        )
