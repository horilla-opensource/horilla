"""
Module containing custom filter classes for various models.
"""

import uuid
import django_filters
from django import forms
from django_filters import FilterSet
from .models import Asset, AssetAssignment, AssetCategory, AssetRequest


class CustomFilterSet(FilterSet):
    """
    Custom FilterSet class that applies specific CSS classes to filter
    widgets.

    The class applies CSS classes to different types of filter widgets,
    such as NumberInput, EmailInput, TextInput, Select, Textarea,
    CheckboxInput, CheckboxSelectMultiple, and ModelChoiceField. The
    CSS classes are applied to enhance the styling and behavior of the
    filter widgets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                    widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                    widget,
                    (
                        forms.CheckboxInput,
                        forms.CheckboxSelectMultiple,
                    ),
            ):
                filter_widget.field.widget.attrs.update(
                    {"class": "oh-switch__checkbox"}
                )
            elif isinstance(widget, (forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 ",
                    }
                )
            elif isinstance(widget, (forms.DateField)):
                filter_widget.field.widget.attrs.update(
                    {"type": "date", "class": "oh-input  w-100"}
                )
            if isinstance(field, django_filters.CharFilter):
                field.lookup_expr = "icontains"


class AssetExportFilter(CustomFilterSet):
    """
    Custom filter class for exporting filtered Asset data.
    """

    class Meta:
        """
        A nested class that specifies the configuration for the filter.
            model(class): The Asset model is used to filter.
            fields (str): A special value "__all__" to include all fields
                          of the model in the filter.
        """

        model = Asset
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AssetExportFilter, self).__init__(*args, **kwargs)
        self.form.fields["asset_purchase_date"].widget.attrs.update({"type": "date"})


class AssetFilter(CustomFilterSet):
    """
    Custom filter set for Asset instances.
    """

    class Meta:
        """
        A nested class that specifies the configuration for the filter.
            model(class): The Asset model is used to filter.
            fields (str): A special value "__all__" to include all fields
                          of the model in the filter.
        """

        model = Asset
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AssetFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs["id"] = str(uuid.uuid4())


class CustomAssetFilter(CustomFilterSet):
    """
    Custom filter set for asset assigned to employees instances.
    """

    asset_id__asset_name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        """
        Specifies the model and fields to be used for filtering AssetAssignment instances.

        Attributes:
        model (class): The model class AssetAssignment to be filtered.
        fields (list): The fields to include in the filter, referring to
                       related AssetAssignment fields.
        """

        model = AssetAssignment
        fields = [
            "asset_id__asset_name",
            "asset_id__asset_status",
        ]

    def __init__(self, *args, **kwargs):
        super(CustomAssetFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs["id"] = str(uuid.uuid4())


class AssetRequestFilter(CustomFilterSet):
    """
    Custom filter set for AssetRequest instances.
    """

    class Meta:
        """
        Specifies the model and fields to be used for filtering AssetRequest instances.

        Attributes:
        model (class): The model class AssetRequest to be filtered.
        fields (str): A special value "__all__" to include all fields of the model in the filter.
        """

        model = AssetRequest
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AssetRequestFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs["id"] = str(uuid.uuid4())


class AssetAllocationFilter(CustomFilterSet):
    """
    Custom filter set for AssetAllocation instances.
    """

    class Meta:
        """
        Specifies the model and fields to be used for filtering AssetAllocation instances.

        Attributes:
            model (class): The model class AssetAssignment to be filtered.
            fields (str): A special value "__all__" to include all fields
                          of the model in the filter.
        """

        model = AssetAssignment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AssetAllocationFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs["id"] = str(uuid.uuid4())


class AssetCategoryFilter(CustomFilterSet):
    """
    Custom filter set for AssetCategory instances.
    """

    class Meta:
        """
        Specifies the model and fields to be used for filtering AssetCategory instances.

        Attributes:
            model (class): The model class AssetCategory to be filtered.
            fields (str): A special value "__all__" to include all fields
                          of the model in the filter.
        """

        model = AssetCategory
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AssetCategoryFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs["id"] = str(uuid.uuid4())
