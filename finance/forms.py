from django import forms
from django.core.exceptions import ValidationError
from .models import EmployeeAllocation, CostDistribution

class EmployeeAllocationForm(forms.ModelForm):
    employee_display = forms.CharField(
        label="Employee", required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )

    class Meta:
        model = EmployeeAllocation
        fields = ['employee', 'percentage_allocation']
        widgets = {
            'employee': forms.HiddenInput(),  # Hidden so the value is submitted
            'percentage_allocation': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.employee:
            self.fields['employee'].initial = self.instance.employee.pk
            self.fields['employee_display'].initial = str(self.instance.employee)
        else:
            self.fields['employee_display'].initial = "No employee assigned"

    def clean_percentage_allocation(self):
        pct = self.cleaned_data.get('percentage_allocation')
        if pct is not None:
            if pct < 0 or pct > 100:
                raise ValidationError("Percentage must be between 0 and 100.")
        return pct

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('employee'):
            raise ValidationError("Employee is required.")
        return cleaned_data


class CostDistributionForm(forms.ModelForm):
    class Meta:
        model = CostDistribution
        fields = ['category', 'percentage']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure fields display current data if an instance exists
        if self.instance and self.instance.pk:
            self.fields['category'].initial = self.instance.category
            self.fields['percentage'].initial = self.instance.percentage

    def clean_percentage(self):
        pct = self.cleaned_data.get('percentage')
        if pct is not None:
            if pct < 0 or pct > 100:
                raise ValidationError("Percentage must be between 0 and 100.")
        return pct

from django import forms
from .models import ProfitDistribution

from django import forms
from django.forms import modelformset_factory
from .models import ProfitDistribution

class ProfitDistributionForm(forms.ModelForm):
    class Meta:
        model = ProfitDistribution
        fields = ['category', 'percentage']

    def clean_percentage(self):
        percentage = self.cleaned_data.get("percentage", 0)
        if percentage < 0 or percentage > 100:
            raise forms.ValidationError("Percentage must be between 0 and 100.")
        return percentage

from django import forms
from django.forms import inlineformset_factory
from .models import AdditionalCost, Project
class AdditionalCostForm(forms.ModelForm):
    class Meta:
        model = AdditionalCost
        fields = ['cost_name', 'cost_value']
        widgets = {
            'cost_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cost_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
AdditionalCostFormSet = inlineformset_factory(
    Project,
    AdditionalCost,
    form=AdditionalCostForm,
    extra=1, 
    can_delete=True
)
