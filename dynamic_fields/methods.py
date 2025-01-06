"""
dynamic_fields/methods.py
"""

from django.db import connection
from django.template.loader import render_to_string

from horilla.horilla_middlewares import _thread_locals


def column_exists(table_name, column_name):
    """
    Check if the column exists in the database table.
    """
    with connection.cursor() as cursor:
        columns = [
            col[0]
            for col in connection.introspection.get_table_description(
                cursor, table_name
            )
        ]
        return column_name in columns


def structured(self):
    """
    Render the form fields as HTML table rows with Bootstrap styling.
    """
    request = getattr(_thread_locals, "request", None)
    context = {
        "form": self,
        "request": request,
    }
    table_html = render_to_string("dynamic_fields/common/form.html", context)
    return table_html
