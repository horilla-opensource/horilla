"""
These forms provide a convenient way to handle data input, validation, and customization
of form fields and widgets for the corresponding models in the payroll management system.
"""

import datetime
import uuid
from typing import Any

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

import payroll.models.models
from base import thread_local_middleware
from base.forms import Form, ModelForm
from base.methods import reload_queryset
from employee.filters import EmployeeFilter
from employee.models import BonusPoint, Employee
from horilla.decorators import logger
from horilla_widgets.forms import HorillaForm
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from leave.models import AvailableLeave, LeaveType
from notifications.signals import notify
from payroll.models import tax_models as models
from payroll.models.models import (
    Allowance,
    Contract,
    Deduction,
    LoanAccount,
    MultipleCondition,
    Payslip,
    Reimbursement,
    ReimbursementMultipleAttachment,
)
from payroll.widgets import component_widgets as widget


class AllowanceForm(forms.ModelForm):
    """
    Form for Allowance model
    """

    load = forms.CharField(widget=widget.AllowanceConditionalVisibility, required=False)
    style = forms.CharField(required=False)
    verbose_name = _("Allowance")

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Allowance
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "one_time_date": forms.DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {}
            if instance.one_time_date is not None:
                initial = {
                    "one_time_date": instance.one_time_date.strftime("%Y-%m-%d"),
                }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["style"].widget = widget.StyleWidget(form=self)

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        super().save(commit)
        other_conditions = self.data.getlist("other_conditions")
        other_fields = self.data.getlist("other_fields")
        other_values = self.data.getlist("other_values")
        multiple_conditions = []
        try:
            if self.instance.pk:
                self.instance.other_conditions.all().delete()
            if self.instance.is_condition_based:
                for index, field in enumerate(other_fields):
                    condition = MultipleCondition(
                        field=field,
                        condition=other_conditions[index],
                        value=other_values[index],
                    )
                    condition.save()
                    multiple_conditions.append(condition)
        except Exception as e:
            logger(e)
        if commit:
            self.instance.other_conditions.add(*multiple_conditions)
        return multiple_conditions


class DeductionForm(forms.ModelForm):
    """
    Form for Deduction model
    """

    load = forms.CharField(widget=widget.DeductionConditionalVisibility, required=False)
    style = forms.CharField(required=False)
    verbose_name = _("Deduction")

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Deduction
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "one_time_date": forms.DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {}
            if instance.one_time_date is not None:
                initial = {
                    "one_time_date": instance.one_time_date.strftime("%Y-%m-%d"),
                }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["style"].widget = widget.StyleWidget(form=self)

    def clean(self):
        if (
            self.data.get("update_compensation") is not None
            and self.data.get("update_compensation") != ""
        ):
            if (
                self.data.getlist("specific_employees") is None
                and len(self.data.getlist("specific_employees")) == 0
            ):
                raise forms.ValidationError(
                    {"specific_employees": _("You need to choose the employee.")}
                )

            if (
                self.data.get("one_time_date") is None
                and self.data.get("one_time_date") == ""
            ):
                raise forms.ValidationError(
                    {"one_time_date": _("This field is required.")}
                )
            if self.data.get("amount") is None and self.data.get("amount") == "":
                raise forms.ValidationError({"amount": _("This field is required.")})
        return super().clean()

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        super().save(commit)
        other_conditions = self.data.getlist("other_conditions")
        other_fields = self.data.getlist("other_fields")
        other_values = self.data.getlist("other_values")
        multiple_conditions = []
        try:
            if self.instance.pk:
                self.instance.other_conditions.all().delete()
            if self.instance.is_condition_based:
                for index, field in enumerate(other_fields):
                    condition = MultipleCondition(
                        field=field,
                        condition=other_conditions[index],
                        value=other_values[index],
                    )
                    condition.save()
                    multiple_conditions.append(condition)
        except Exception as e:
            print(e)
        if commit:
            self.instance.other_conditions.add(*multiple_conditions)
        return multiple_conditions


class PayslipForm(ModelForm):
    """
    Form for Payslip
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_contracts = Contract.objects.filter(contract_status="active")
        self.fields["employee_id"].choices = [
            (contract.employee_id.id, contract.employee_id)
            for contract in active_contracts
            if contract.employee_id.is_active
        ]
        if self.instance.pk is None:
            self.initial["start_date"] = datetime.date.today().replace(day=1)
            self.initial["end_date"] = datetime.date.today()

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Payslip
        fields = [
            "employee_id",
            "start_date",
            "end_date",
        ]
        exclude = ["is_active"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }


class GeneratePayslipForm(HorillaForm):
    """
    Form for Payslip
    """

    group_name = forms.CharField(
        label="Batch name",
        required=False,
        # help_text="Enter +-something if you want to generate payslips by batches",
    )
    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.none(),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
        ),
        label="Employee",
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        today = datetime.date.today()
        if end_date < start_date:
            raise forms.ValidationError(
                {
                    "end_date": "The end date must be greater than or equal to the start date."
                }
            )
        if start_date > today:
            raise forms.ValidationError(
                {"end_date": "The start date cannot be in the future."}
            )

        if end_date > today:
            raise forms.ValidationError(
                {"end_date": "The end date cannot be in the future."}
            )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].queryset = Employee.objects.filter(
            is_active=True,
            contract_set__isnull=False,
            contract_set__contract_status="active",
        )
        self.fields["employee_id"].widget.attrs.update(
            {"class": "oh-select oh-select-2", "id": uuid.uuid4()}
        )
        self.fields["start_date"].widget.attrs.update({"class": "oh-input w-100"})
        self.fields["group_name"].widget.attrs.update({"class": "oh-input w-100"})
        self.fields["end_date"].widget.attrs.update({"class": "oh-input w-100"})
        self.initial["start_date"] = datetime.date.today().replace(day=1)
        self.initial["end_date"] = datetime.date.today()

    class Meta:
        """
        Meta class for additional options
        """

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PayrollSettingsForm(ModelForm):
    """
    Form for PayrollSettings model
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = models.PayrollSettings
        fields = "__all__"


excel_columns = [
    ("employee_id", _("Employee")),
    ("group_name", _("Batch")),
    ("start_date", _("Start Date")),
    ("end_date", _("End Date")),
    ("contract_wage", _("Contract Wage")),
    ("basic_pay", _("Basic Pay")),
    ("gross_pay", _("Gross Pay")),
    ("deduction", _("Deduction")),
    ("net_pay", _("Net Pay")),
    ("status", _("Status")),
    ("employee_id__employee_bank_details__bank_name", _("Bank Name")),
    ("employee_id__employee_bank_details__branch", _("Branch")),
    ("employee_id__employee_bank_details__account_number", _("Account Number")),
    ("employee_id__employee_bank_details__any_other_code1", _("Bank Code #1")),
    ("employee_id__employee_bank_details__any_other_code2", _("Bank Code #2")),
    ("employee_id__employee_bank_details__country", _("Country")),
    ("employee_id__employee_bank_details__state", _("State")),
    ("employee_id__employee_bank_details__city", _("City")),
]


class PayslipExportColumnForm(forms.Form):
    selected_fields = forms.MultipleChoiceField(
        choices=excel_columns,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "group_name",
            "start_date",
            "end_date",
            "basic_pay",
            "gross_pay",
            "net_pay",
            "status",
        ],
    )


exclude_fields = ["id", "contract_document", "is_active", "note", "note", "created_at"]


class ContractExportFieldForm(forms.Form):
    model_fields = Contract._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in exclude_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "contract_name",
            "employee_id",
            "contract_start_date",
            "contract_end_date",
            "wage_type",
            "wage",
            "filing_status",
            "contract_status",
        ],
    )


class BonusForm(Form):
    """
    Bonus Creating Form
    """

    title = forms.CharField(max_length=100)
    date = forms.DateField(widget=forms.DateInput())
    employee_id = forms.IntegerField(label="Employee", widget=forms.HiddenInput())
    amount = forms.DecimalField(label="Amount")

    def save(self, commit=True):
        title = self.cleaned_data["title"]
        date = self.cleaned_data["date"]
        employee_id = self.cleaned_data["employee_id"]
        amount = self.cleaned_data["amount"]

        bonus = Allowance()
        bonus.title = title
        bonus.one_time_date = date
        bonus.only_show_under_employee = True
        bonus.amount = amount
        bonus.is_fixed = True
        bonus.save()
        bonus.include_active_employees = False
        bonus.specific_employees.set([employee_id])
        bonus.save()

        return bonus

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "oh-input w-100"})
        self.fields["date"].widget = forms.DateInput(
            attrs={"type": "date", "class": "oh-input w-100"}
        )


class PayslipAllowanceForm(BonusForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].widget = forms.HiddenInput()


class PayslipDeductionForm(ModelForm):
    """
    Bonus Creating Form
    """

    verbose_name = _("Deduction")

    class Meta:
        model = Deduction
        fields = [
            "title",
            "one_time_date",
            "update_compensation",
            "is_tax",
            "is_pretax",
            "is_fixed",
            "amount",
            "based_on",
            "rate",
            "employer_rate",
            "has_max_limit",
            "maximum_amount",
        ]
        widgets = {
            "one_time_date": forms.HiddenInput(),
        }

    # employee_id = forms.IntegerField(label="Employee", widget=forms.HiddenInput())

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("one_time_deduction.html", context)
        return table_html


class LoanAccountForm(ModelForm):
    """
    LoanAccountForm
    """

    verbose_name = "Loan / Advanced Sarlary"

    class Meta:
        model = LoanAccount
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "provided_date": forms.DateTimeInput(attrs={"type": "date"}),
            "installment_start_date": forms.DateTimeInput(attrs={"type": "date"}),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["installment_start_date"] = str(datetime.date.today())
        if self.instance.pk:
            self.verbose_name = self.instance.title
            fields_to_exclude = ["employee_id", "installment_start_date"]
            if Payslip.objects.filter(
                installment_ids__in=list(
                    self.instance.deduction_ids.values_list("id", flat=True)
                )
            ).exists():
                fields_to_exclude = fields_to_exclude + ["loan_amount", "installments"]
            self.initial["provided_date"] = str(self.instance.provided_date)
            for field in fields_to_exclude:
                if field in self.fields:
                    del self.fields[field]


class AssetFineForm(LoanAccountForm):
    verbose_name = "Asset Fine"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["loan_amount"].label = "Fine Amount"
        fields_to_exclude = ["employee_id", "provided_date", "type"]
        for field in fields_to_exclude:
            if field in self.fields:
                del self.fields[field]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result[0] if result else None


class ReimbursementForm(ModelForm):
    """
    ReimbursementForm
    """

    verbose_name = "Reimbursement / Encashment"

    class Meta:
        model = Reimbursement
        fields = "__all__"
        exclude = ["is_active"]

    def get_encashable_leaves(self, employee):
        leaves = LeaveType.objects.filter(
            employee_available_leave__employee_id=employee,
            employee_available_leave__total_leave_days__gte=1,
            is_encashable=True,
        )
        return leaves

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclude_fields = []
        if not self.instance.pk:
            self.initial["allowance_on"] = str(datetime.date.today())

        request = getattr(thread_local_middleware._thread_locals, "request", None)
        if request:
            employee = (
                request.user.employee_get
                if self.instance.pk is None
                else self.instance.employee_id
            )
        self.initial["employee_id"] = employee.id
        assigned_leaves = self.get_encashable_leaves(employee)
        self.assigned_leaves = AvailableLeave.objects.filter(
            leave_type_id__in=assigned_leaves, employee_id=employee
        )
        self.fields["leave_type_id"].queryset = assigned_leaves
        self.fields["leave_type_id"].empty_label = None
        self.fields["employee_id"].empty_label = None

        type_attr = self.fields["type"].widget.attrs
        type_attr["onchange"] = "toggleReimbursmentType($(this))"
        self.fields["type"].widget.attrs.update(type_attr)

        employee_attr = self.fields["employee_id"].widget.attrs
        employee_attr["onchange"] = "getAssignedLeave($(this))"
        self.fields["employee_id"].widget.attrs.update(employee_attr)

        self.fields["allowance_on"].widget = forms.DateInput(
            attrs={"type": "date", "class": "oh-input w-100"}
        )
        self.fields["attachment"] = MultipleFileField(label="Attachements")

        # deleting fields based on type
        type = None
        if self.data and not self.instance.pk:
            type = self.data["type"]
        elif self.instance is not None:
            type = self.instance.type
        if not request.user.has_perm("payroll.add_reimbursement"):
            exclude_fields.append("employee_id")

        if type == "reimbursement" and self.instance.pk:
            exclude_fields = exclude_fields + [
                "leave_type_id",
                "cfd_to_encash",
                "ad_to_encash",
                "bonus_to_encash",
            ]
        elif (
            self.instance.pk
            and type == "leave_encashment"
            or self.data.get("type") == "leave_encashment"
        ):
            exclude_fields = exclude_fields + [
                "attachment",
                "amount",
                "bonus_to_encash",
            ]
        elif (
            self.instance.pk
            and type == "bonus_encashment"
            or self.data.get("type") == "bonus_encashment"
        ):
            exclude_fields = exclude_fields + [
                "attachment",
                "amount",
                "leave_type_id",
                "cfd_to_encash",
                "ad_to_encash",
            ]
        if self.instance.pk:
            exclude_fields = exclude_fields + ["type", "employee_id"]

        for field in exclude_fields:
            if field in self.fields:
                del self.fields[field]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        if self.instance.pk:
            employee_id = self.instance.employee_id
            type = self.instance.type

        else:
            employee_id = request.user.employee_get
            type = cleaned_data["type"]

        available_points = BonusPoint.objects.filter(employee_id=employee_id).first()
        if type == "bonus_encashment":
            if self.instance.pk:
                bonus_to_encash = self.instance.bonus_to_encash
            else:
                bonus_to_encash = cleaned_data["bonus_to_encash"]

            if available_points.points < bonus_to_encash:
                raise forms.ValidationError(
                    {"bonus_to_encash": "Not enough bonus points to redeem"}
                )
            if bonus_to_encash <= 0:
                raise forms.ValidationError(
                    {"bonus_to_encash": "Points must be greater than zero to redeem."}
                )
        if type == "leave_encashment":
            if self.instance.pk:
                leave_type_id = self.instance.leave_type_id
                cfd_to_encash = self.instance.cfd_to_encash
                ad_to_encash = self.instance.ad_to_encash
            else:
                leave_type_id = cleaned_data["leave_type_id"]
                cfd_to_encash = cleaned_data["cfd_to_encash"]
                ad_to_encash = cleaned_data["ad_to_encash"]
            encashable_leaves = self.get_encashable_leaves(employee_id)
            if leave_type_id is None:
                raise forms.ValidationError({"leave_type_id": "This field is required"})
            elif leave_type_id not in encashable_leaves:
                raise forms.ValidationError(
                    {"leave_type_id": "This leave type is not encashable"}
                )
            else:
                available_leave = AvailableLeave.objects.filter(
                    leave_type_id=leave_type_id, employee_id=employee_id
                ).first()
                if cfd_to_encash < 0:
                    raise forms.ValidationError(
                        {"cfd_to_encash": _("Value can't be negative.")}
                    )
                if ad_to_encash < 0:
                    raise forms.ValidationError(
                        {"ad_to_encash": _("Value can't be negative.")}
                    )
                if cfd_to_encash > available_leave.carryforward_days:
                    raise forms.ValidationError(
                        {"cfd_to_encash": _("Not enough carryforward days to redeem")}
                    )
                if ad_to_encash > available_leave.available_days:
                    raise forms.ValidationError(
                        {"ad_to_encash": _("Not enough available days to redeem")}
                    )

    def save(self, commit: bool = ...) -> Any:
        is_new = not self.instance.pk
        attachemnt = []
        multiple_attachment_ids = []
        attachemnts = None
        if self.files.getlist("attachment"):
            attachemnts = self.files.getlist("attachment")
            self.instance.attachemnt = attachemnts[0]
            multiple_attachment_ids = []
            for attachemnt in attachemnts:
                file_instance = ReimbursementMultipleAttachment()
                file_instance.attachment = attachemnt
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        instance.other_attachments.add(*multiple_attachment_ids)

        emp = Employee.objects.get(id=self.initial["employee_id"])
        try:
            if is_new:
                notify.send(
                    emp,
                    recipient=(
                        emp.employee_work_info.reporting_manager_id.employee_user_id
                    ),
                    verb=f"You have a new reimbursement request to approve for {emp}.",
                    verb_ar=f"لديك طلب استرداد نفقات جديد يتعين عليك الموافقة عليه لـ {emp}.",
                    verb_de=f"Sie haben einen neuen Rückerstattungsantrag zur Genehmigung für {emp}.",
                    verb_es=f"Tienes una nueva solicitud de reembolso para aprobar para {emp}.",
                    verb_fr=f"Vous avez une nouvelle demande de remboursement à approuver pour {emp}.",
                    icon="information",
                    redirect=f"/payroll/view-reimbursement?id={instance.id}",
                )
        except Exception as e:
            pass

        return instance, attachemnts


class ConditionForm(ModelForm):
    """
    Multiple condition form
    """

    class Meta:
        model = Allowance
        fields = [
            "field",
            "condition",
            "value",
        ]
