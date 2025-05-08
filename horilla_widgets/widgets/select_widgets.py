"""
select_widgets.py

This module is used to write horilla form select widgets
"""

import uuid

from django import forms

from horilla import horilla_middlewares

ALL_INSTANCES = {}


def get_short_uuid(length: int, prefix: str = "widget"):
    """
    Short uuid generating method
    """
    uuid_str = str(uuid.uuid4().hex)
    return prefix + str(uuid_str[:length]).replace("-", "")


class HorillaMultiSelectWidget(forms.Widget):
    """
    HorillaMultiSelectWidget
    """

    def __init__(
        self,
        *args,
        filter_route_name,
        filter_class=None,
        filter_instance_contex_name=None,
        filter_template_path=None,
        instance=None,
        required=False,
        form=None,
        help_text=None,
        **kwargs
    ) -> None:
        self.filter_route_name = filter_route_name
        self.required = required
        self.filter_class = filter_class
        self.filter_instance_contex_name = filter_instance_contex_name
        self.filter_template_path = filter_template_path
        self.instance = instance
        self.form = form
        self.help_text = help_text
        super().__init__()

    template_name = "horilla_widgets/horilla_multiselect_widget.html"

    def get_context(self, name, value, attrs):
        # Get the default context from the parent class
        context = super().get_context(name, value, attrs)
        # Add your custom data to the context
        queryset = self.choices.queryset
        field = self.choices.field
        context["queryset"] = queryset
        context["field_name"] = name
        if self.form and name in self.form.data:
            initial = self.form.data.getlist(name)
            context["initial"] = initial
        elif value:
            context["initial"] = value

        elif self.instance and self.instance.pk:
            initial = list(getattr(self.instance, name).values_list("id", flat=True))
            context["initial"] = initial
        else:
            context["initial"] = []
        context["field"] = field
        context["self"] = self
        context["filter_template_path"] = self.filter_template_path
        context["filter_route_name"] = self.filter_route_name
        context["required"] = self.required
        context["help_text"] = self.help_text
        self.attrs["id"] = (
            ("id_" + name) if self.attrs.get("id") is None else self.attrs.get("id")
        )
        uid = get_short_uuid(5)
        context["section_id"] = uid
        context[self.filter_instance_contex_name] = self.filter_class
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        ALL_INSTANCES[str(request.user.id)] = self

        return context
