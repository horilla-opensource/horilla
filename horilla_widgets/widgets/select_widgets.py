"""
select_widgets.py

This module is used to write horilla form select widgets
"""
from django import forms


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
        **kwargs
    ) -> None:
        self.filter_route_name = filter_route_name
        self.required = required
        self.filter_class = filter_class
        self.filter_instance_contex_name = filter_instance_contex_name
        self.filter_template_path = filter_template_path
        self.instance = instance
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
        context["field"] = field
        context["self"] = self
        context["filter_template_path"] = self.filter_template_path
        context["filter_route_name"] = self.filter_route_name
        context["required"] = self.required
        self.attrs["id"] = ("id_" + name ) if self.attrs.get('id') is None else self.attrs.get("id")
        context[self.filter_instance_contex_name] = self.filter_class
        return context
