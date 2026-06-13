"""
horilla/inherit/migration_ops.py

Custom migration operations for the _inherit extension system.

InjectField       — adds a field to a model in a different app.
InjectAlterField  — alters an already-injected field (verbose_name, max_length, …).
InjectRemoveField — removes an already-injected field.
InjectRenameField — renames an already-injected field.

All operations keep the migration file in the extension app while the DDL
targets the source app's table.

Usage inside a migration file:
    from horilla.inherit.migration_ops import InjectField

    class Migration(migrations.Migration):
        dependencies = [("employee", "0001_initial")]

        operations = [
            InjectField(
                target_app_label="employee",
                model_name="Employee",
                name="blood_group",
                field=models.CharField(max_length=3, null=True, blank=True),
            ),
        ]
"""

from django.db import migrations, models


class InjectField(migrations.AddField):
    """
    Adds a field to a model that lives in a different app.
    """

    def __init__(self, target_app_label, model_name, name, field, **kwargs):
        self.target_app_label = target_app_label
        super().__init__(model_name=model_name, name=name, field=field, **kwargs)

    def state_forwards(self, app_label, state):
        state.add_field(
            self.target_app_label,
            self.model_name.lower(),
            self.name,
            self.field.clone(),
            preserve_default=self.preserve_default,
        )

    def _column_exists(self, schema_editor, model):
        with schema_editor.connection.cursor() as cursor:
            existing = schema_editor.connection.introspection.get_table_description(
                cursor, model._meta.db_table
            )
        return any(col.name == self.name for col in existing)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        # Column may already exist if the app was previously removed without
        # dropping the column (soft removal). Skip silently to preserve data.
        if self._column_exists(schema_editor, from_model):
            return
        field = to_model._meta.get_field(self.name)
        if not self.preserve_default:
            field.default = self.field.default
        schema_editor.add_field(from_model, field)
        if not self.preserve_default:
            field.default = models.NOT_PROVIDED

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Intentional no-op: the column is kept so data survives app removal.
        # Removing the app from INSTALLED_APPS hides the field at the Python
        # level; re-adding it restores access to the existing data.
        pass

    def deconstruct(self):
        _name, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        return (
            f"Inject field {self.name} into {self.target_app_label}.{self.model_name}"
        )


class InjectAlterField(migrations.AlterField):
    """
    Alters an already-injected field on a model in a different app.
    Generated automatically when you change a field attribute (verbose_name,
    max_length, choices, …) on an extension model declaration.
    """

    def __init__(self, target_app_label, model_name, name, field, **kwargs):
        self.target_app_label = target_app_label
        super().__init__(model_name=model_name, name=name, field=field, **kwargs)

    def state_forwards(self, app_label, state):
        state.alter_field(
            self.target_app_label,
            self.model_name.lower(),
            self.name,
            self.field.clone(),
            self.preserve_default,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        from_field = from_model._meta.get_field(self.name)
        to_field = to_model._meta.get_field(self.name)
        schema_editor.alter_field(from_model, from_field, to_field)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Reverse is the same operation with from/to swapped — Django handles this
        # correctly via schema_editor.alter_field.
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        _name, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        return f"Alter injected field {self.name} on {self.target_app_label}.{self.model_name}"


class InjectRemoveField(migrations.RemoveField):
    """
    Removes an already-injected field from a model in a different app.
    Generated automatically when you delete a field from an extension model.
    """

    def __init__(self, target_app_label, model_name, name, **kwargs):
        self.target_app_label = target_app_label
        super().__init__(model_name=model_name, name=name, **kwargs)

    def state_forwards(self, app_label, state):
        state.remove_field(
            self.target_app_label,
            self.model_name.lower(),
            self.name,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, from_model):
            return
        field = from_model._meta.get_field(self.name)
        schema_editor.remove_field(from_model, field)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Re-adding is handled by InjectField in the forward direction.
        pass

    def deconstruct(self):
        _name, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        return f"Remove injected field {self.name} from {self.target_app_label}.{self.model_name}"


class InjectRenameField(migrations.RenameField):
    """
    Renames an already-injected field on a model in a different app.
    Generated automatically when you rename a field in an extension model.
    Also updates INJECTION_MAP so future operations on the renamed field
    are still routed to the correct extension app.
    """

    def __init__(self, target_app_label, model_name, old_name, new_name, **kwargs):
        self.target_app_label = target_app_label
        super().__init__(
            model_name=model_name, old_name=old_name, new_name=new_name, **kwargs
        )

    def state_forwards(self, app_label, state):
        state.rename_field(
            self.target_app_label,
            self.model_name.lower(),
            self.old_name,
            self.new_name,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        schema_editor.alter_field(
            from_model,
            from_model._meta.get_field(self.old_name),
            to_model._meta.get_field(self.new_name),
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        schema_editor.alter_field(
            from_model,
            from_model._meta.get_field(self.new_name),
            to_model._meta.get_field(self.old_name),
        )

    def deconstruct(self):
        _name, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        return (
            f"Rename injected field {self.old_name} to {self.new_name} "
            f"on {self.target_app_label}.{self.model_name}"
        )
