"""
forms.py
Asset Management Forms

This module contains Django ModelForms for handling various aspects of asset management,
including asset creation, allocation, return, category assignment, and batch handling.
"""
from datetime import date
import uuid
from django import forms
from base.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from employee.models import Employee
from asset.models import Asset, AssetRequest, AssetAssignment, AssetCategory, AssetLot
from base.methods import reload_queryset


def set_date_field_initial(instance):
    """this is used to update change the date value format"""
    initial = {}
    if instance.asset_purchase_date is not None:
        initial["asset_purchase_date"] = instance.asset_purchase_date.strftime(
            "%Y-%m-%d"
        )

    return initial


class AssetForm(ModelForm):
    """
    A ModelForm for creating and updating asset information.
    """

    class Meta:
        """
        Specifies the model and fields to be used for the AssetForm.
        Attributes:
            model (class): The model class Asset to be used for the form.
            fields (str): A special value "__all__" to include all fields
                          of the model in the form.
        """

        model = Asset
        fields = "__all__"
        widgets = {
            "asset_name": forms.TextInput(
                attrs={"placeholder": "Macbook Pro.", "class": "oh-input w-100"}
            ),
            "asset_description": forms.Textarea(
                attrs={
                    "type": "text",
                    "placeholder": _("A powerful laptop for business use."),
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "rows": 3,
                    "cols": 40,
                }
            ),
            "asset_tracking_id": forms.TextInput(
                attrs={"placeholder": "LPT001", "class": "oh-input w-100"}
            ),
            "asset_purchase_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "asset_purchase_cost": forms.NumberInput(
                attrs={"class": "oh-input w-100", "placeholder": "1200.00."}
            ),
            "asset_category_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                },
            ),
            "asset_status": forms.Select(
                attrs={"class": "oh-select oh-select--lg oh-select-no-search "}
            ),
            "asset_lot_number_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible  ",
                    "placeholder": "LOT001",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance:
            kwargs["initial"] = set_date_field_initial(instance)
        super(AssetForm, self).__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["asset_category_id"].widget.attrs.update({"id": str(uuid.uuid4())})
        self.fields["asset_lot_number_id"].widget.attrs.update(
            {"id": str(uuid.uuid4())}
        )
        self.fields["asset_status"].widget.attrs.update({"id": str(uuid.uuid4())})

    def clean(self):
        instance = self.instance
        if instance.pk:
            if asset_in_use := instance.assetassignment_set.filter(
                return_status__isnull=True
            ):
                raise ValidationError('Asset in use you can"t change the status')
            if (
                Asset.objects.filter(asset_tracking_id=self.data["asset_tracking_id"])
                .exclude(id=instance.pk)
                .exists()
            ):
                raise ValidationError(
                    {"asset_tracking_id": "Already asset with this tracking id exists."}
                )


class AssetCategoryForm(ModelForm):
    """
    A form for creating and updating AssetCategory instances.
    """

    class Meta:
        """
        Specifies the model and fields to be used for the AssetForm.
        Attributes:
            model (class): The model class AssetCategory to be used for the form.
            fields (str): A special value "__all__" to include all fields
                          of the model in the form.
            widgets (dict): A dictionary containing widget configurations for
                            specific form fields.
        """

        model = AssetCategory
        fields = "__all__"
        widgets = {
            "asset_category_name": forms.TextInput(
                attrs={"placeholder": _("Computers."), "class": "oh-input w-100"}
            ),
            "asset_category_description": forms.Textarea(
                attrs={
                    "type": "text",
                    "placeholder": _("A category for all types of laptops."),
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "rows": 3,
                    "cols": 40,
                }
            ),
        }


class AssetRequestForm(ModelForm):
    """
    A Django ModelForm for creating and updating AssetRequest instances.
    """

    class Meta:
        """
        Specifies the model and fields to be used for the AssetRequestForm.
        Attributes:
            model (class): The model class AssetRequest to be used for the form.
            fields (str): A special value "__all__" to include all fields
                          of the model in the form.
            widgets (dict): A dictionary containing widget configurations for
                            specific form fields.
        """

        model = AssetRequest
        fields = "__all__"
        widgets = {
            "requested_employee_id": forms.Select(
                attrs={
                    "class": "oh-select  oh-select-2 select2-hidden-accessible",
                }
            ),
            "asset_category_id": forms.Select(
                attrs={
                    "class": "oh-select  oh-select-2 select2-hidden-accessible",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "type": "text",
                    "id": "objective_description",
                    "placeholder": _(
                        "Requesting a laptop for software development purposes."
                    ),
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "rows": 3,
                    "cols": 40,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(AssetRequestForm, self).__init__(
            *args,
            **kwargs,
        )
        reload_queryset(self.fields)
        if user is not None and user.has_perm("asset.add_assetrequest"):
            self.fields["requested_employee_id"].queryset = Employee.objects.all()
            self.fields["requested_employee_id"].initial = Employee.objects.filter(
                id=user.employee_get.id
            ).first()
        else:
            self.fields["requested_employee_id"].queryset = Employee.objects.filter(
                employee_user_id=user
            )
            self.fields["requested_employee_id"].initial = user.employee_get

        self.fields["asset_category_id"].widget.attrs.update({"id": str(uuid.uuid4())})


class AssetAllocationForm(ModelForm):
    """
    A Django ModelForm for creating and updating AssetAssignment instances.
    """

    def __init__(self, *args, **kwargs):
        super(AssetAllocationForm, self).__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["asset_id"].queryset = Asset.objects.filter(
            asset_status="Available"
        )

    class Meta:
        """
        Specifies the model and fields to be used for the AssetAllocationForm.
        Attributes:
            model (class): The model class AssetAssignment to be used for the form.
            fields (str): A special value "__all__" to include all fields
                          of the model in the form.
            widgets (dict): A dictionary containing widget configurations for
                            specific form fields.
        """

        model = AssetAssignment
        fields = "__all__"
        exclude = ["return_date", "return_condition", "assigned_date"]
        widgets = {
            "asset_id": forms.Select(attrs={"class": "oh-select oh-select-2 "}),
            "assigned_to_employee_id": forms.Select(
                attrs={"class": "oh-select oh-select-2 "}
            ),
            "assigned_by_employee_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 ",
                },
            ),
        }


class AssetReturnForm(ModelForm):
    """
    A Django ModelForm for updating AssetAssignment instances during asset return.
    """

    class Meta:
        """
        Specifies the model and fields to be used for the AssetReturnForm.
        Attributes:
            model (class): The model class AssetAssignment to be used for the form.
            fields (list): The fields to include in the form, referring to
                           related AssetAssignment fields.
            widgets (dict): A dictionary containing widget configurations for
                            specific form fields.
        """

        model = AssetAssignment
        fields = ["return_date", "return_condition", "return_status"]
        widgets = {
            "return_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input w-100", "required": "true"}
            ),
            "return_condition": forms.Textarea(
                attrs={
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "rows": 3,
                    "cols": 40,
                    "placeholder": _(
                        "on returns the laptop. However, it has suffered minor damage."
                    ),
                }
            ),
            "return_status": forms.Select(
                attrs={"class": "oh-select oh-select-2", "required": "true"},
            ),
        }

    def clean_return_date(self):
        return_date = self.cleaned_data.get("return_date")

        if return_date and return_date > date.today():
            raise forms.ValidationError(_("Return date cannot be in the future."))

        return return_date


class AssetBatchForm(ModelForm):
    """
    A Django ModelForm for creating or updating AssetLot instances.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

    class Meta:
        """
        Specifies the model and fields to be used for the AssetBatchForm.
        Attributes:
            model (class): The model class AssetLot to be used for the form.
            fields (str): A special value "__all__" to include all fields
                          of the model in the form.
            widgets (dict): A dictionary containing widget configurations for
                            specific form fields.
        """

        model = AssetLot
        fields = "__all__"
        widgets = {
            "lot_number": forms.TextInput(
                attrs={"placeholder": "A12345.", "class": "oh-input w-100"}
            ),
            "lot_description": forms.Textarea(
                attrs={
                    "type": "text",
                    "placeholder": _(
                        "A batch of 50 laptops, consisting of Lenovo ThinkPad T480s\
                              and Dell XPS 13."
                    ),
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "rows": 3,
                    "cols": 40,
                }
            ),
        }
