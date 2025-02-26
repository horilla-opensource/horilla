import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from simple_history.models import HistoricalRecords

from dynamic_fields.methods import column_exists
from dynamic_fields.models import DynamicField

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command
    """

    help = "Save all instances of the specified model"

    def add_arguments(self, parser):
        parser.add_argument(
            "pk",
            type=str,
            help="Primary key of the DynamicField model to \
                save instances for (e.g., employee.models.Model)",
        )

    def handle(self, *args, **kwargs):
        pk = kwargs["pk"]
        editor = BaseDatabaseSchemaEditor(connection)
        instance = DynamicField.objects.get(pk=pk)
        model = instance.get_model()
        field = instance.get_field()
        field.set_attributes_from_name(instance.field_name)
        sql_delete_column = editor.sql_delete_column.replace("CASCADE", "")
        if column_exists(model._meta.db_table, instance.field_name):
            sql = sql_delete_column % {
                "table": editor.quote_name(model._meta.db_table),
                "column": editor.quote_name(field.column),
            }
            logger.info(f"Field exist, deleting it from {model.__class__.__name__}.")
            editor.execute(sql)

        models.Model.delete(instance, *(), **{})

        name = HistoricalRecords().get_history_model_name(model).lower()
        historical_model_ct = ContentType.objects.filter(model=name).first()
        if historical_model_ct:
            history_model = historical_model_ct.model_class()
            if column_exists(history_model._meta.db_table, instance.field_name):
                sql = editor.sql_delete_column % {
                    "table": editor.quote_name(history_model._meta.db_table),
                    "column": editor.quote_name(field.column),
                }
                logger.info(
                    f"Field exist, deleting it from {history_model.__class__.__name__}."
                )
