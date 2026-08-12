"""
Custom form widgets for conditional visibility and styling.
"""

import os

from django import forms
from django.utils.safestring import SafeText, mark_safe

from horilla import settings


def _static_file_version(*rel_path_parts):
    """
    File mtime, used as a cache-busting query param on hand-loaded script
    tags (these aren't run through {% static %}/ManifestStaticFilesStorage,
    so nothing else invalidates the browser cache when the file changes).
    """
    try:
        path = os.path.join(settings.BASE_DIR, "static", *rel_path_parts)
        return int(os.path.getmtime(path))
    except OSError:
        return 0


class AllowanceConditionalVisibility(forms.Widget):
    """
    A custom widget that loads conditional js to the form.

    Example:
    class MyForm(forms.Form):
        my_field = forms.CharField(widget=AllowanceConditionalVisibility, required=False)

    """

    def render(self, name, value, attrs=None, renderer=None):
        # Exclude the label from the rendered HTML
        version = _static_file_version("build", "js", "allowanceWidget.js")
        rendered_script = f'<script src="/{settings.STATIC_URL}build/js/allowanceWidget.js?v={version}"></script>'
        additional_script = f"""
        <script id="{name}Script">
            $(document).ready(function () {{
                $("[for='id_{name}']").remove()
                $("#{name}Script").remove()
            }});
        </script>
        """
        attrs = attrs or {}
        attrs["required"] = False
        return mark_safe(rendered_script + additional_script)


class DeductionConditionalVisibility(forms.Widget):
    """
    A custom widget that loads conditional js to the form.

    Example:
    class MyForm(forms.Form):
        my_field = forms.CharField(widget=DeductionConditionalVisibility, required=False)

    """

    def render(self, name, value, attrs, renderer) -> SafeText:
        # Exclude the label from the rendered HTML
        version = _static_file_version("build", "js", "deductionWidget.js")
        rendered_script = f'<script src="/{settings.STATIC_URL}build/js/deductionWidget.js?v={version}"></script>'
        additional_script = f"""
        <script id="{name}Script">
            $(document).ready(function () {{
                $("[for='id_{name}']").remove()
                $("#{name}Script").remove()
            }});
        </script>
        """
        attrs = attrs or {}
        attrs["required"] = False
        return mark_safe(rendered_script + additional_script)


class StyleWidget(forms.Widget):
    """
    A custom widget that enhances the styling and functionality of elements.

    Example:
    class MyForm(forms.Form):
        my_field = forms.CharField(widget=styleWidget, required=False)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['style'].widget = widget.styleWidget(form=self)

    """

    def __init__(self, *args, form=None, **kwargs):
        if form is not None:
            for _, field in form.fields.items():
                field.widget.attrs.update(
                    {"data-widget": "style-widget", "class": "style-widget"}
                )
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        """
        Renders the widget as HTML, including the necessary scripts and styles for select2.

        Args:
            name (str): The name of the form field.
            value (Any): The current value of the form field.
            attrs (dict, optional): Additional HTML attributes for the widget.
            renderer: A custom renderer to use, if applicable.

        Returns:
            str: The rendered HTML representation of the widget.
        """
        version = _static_file_version("build", "js", "styleWidget.js")
        rendered_script = f'<script src="/{settings.STATIC_URL}build/js/styleWidget.js?v={version}"></script>'
        additional_script = f"""
        <script id="{name}Script">
            $(document).ready(function () {{
                $("[for='id_{name}']").remove()
                $("#{name}Script").remove()
                // Select all select elements with select2 initialized
                var selects = $("select[data-widget='style-widget']").select2();
                function toggleSelect2() {{
                    selects.each(function() {{
                        var select = $(this);
                        var select2Container = select.nextAll(".select2.select2-container").first();
                        if (select.is(":hidden")) {{
                        select2Container.hide();
                        }} else {{
                            select2Container.show();
                        }}
                    }});
                }}
                $("select, [type='checkbox'], [type='radio']").change(function (e) {{
                    e.preventDefault();
                    toggleSelect2();
                }});
                toggleSelect2();
            }});
        </script>
        <link rel="stylesheet" type="text/css" href="/{settings.STATIC_URL}build/css/styleWidget.css">
        """
        attrs = attrs or {}
        attrs["required"] = False
        return mark_safe(rendered_script + additional_script)
