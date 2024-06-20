"""
Module containing custom filter classes for various models.
"""

import uuid

import django_filters
from django import forms
from django_filters import FilterSet

from base.methods import reload_queryset

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
        reload_queryset(self.form.fields)
        for field_name, field in self.form.fields.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update({"class": "oh-input w-100"})
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
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 ",
                    }
                )
            elif isinstance(widget, (forms.DateField)):
                field.widget.attrs.update({"type": "date", "class": "oh-input  w-100"})
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

    search = django_filters.CharFilter(method="search_method")

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(
                    requested_employee_id__employee_first_name__icontains=split
                )
                | queryset.filter(
                    requested_employee_id__employee_last_name__icontains=split
                )
            )
        return empty.distinct()

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

    search = django_filters.CharFilter(method="search_method")

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(
                    assigned_to_employee_id__employee_first_name__icontains=split
                )
                | queryset.filter(
                    assigned_to_employee_id__employee_last_name__icontains=split
                )
            )
        return empty.distinct()

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


class AssetRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("requested_employee_id", "Employee"),
        ("asset_category_id", "Asset Category"),
        ("asset_request_date", "Request Date"),
        ("asset_request_status", "Status"),
    ]


class AssetAllocationReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("assigned_to_employee_id", "Employee"),
        ("assigned_date", "Assigned Date"),
        ("return_date", "Return Date"),
    ]


class AssetHistoryFilter(CustomFilterSet):
    """
    Custom filter set for AssetAssignment instances for filtering in asset history view.
    """

    search = django_filters.CharFilter(
        field_name="asset_id__asset_name", lookup_expr="icontains"
    )
    returned_assets = django_filters.CharFilter(
        field_name="return_status", method="exclude_none"
    )
    return_date_gte = django_filters.DateFilter(
        field_name="return_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    return_date_lte = django_filters.DateFilter(
        field_name="return_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    assigned_date_gte = django_filters.DateFilter(
        field_name="assigned_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    assigned_date_lte = django_filters.DateFilter(
        field_name="assigned_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def exclude_none(self, queryset, name, value):
        """
        Exclude objects with a null return_status from the queryset if value is "True"
        """
        if value == "True":
            queryset = queryset.filter(return_status__isnull=False)
        return queryset

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


class AssetHistoryReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("asset_id", "Asset"),
        ("assigned_to_employee_id", "Employee"),
        ("assigned_date", "Assigned Date"),
        ("return_date", "Return Date"),
    ]
