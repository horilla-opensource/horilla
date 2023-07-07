from django.forms import ModelForm
from .models import *
from django.forms import DateInput
from django.forms.widgets import TextInput
from django import forms
from employee.models import Employee
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re
  

CHOICES = [("yes", _("Yes")), ("no", _("No"))]

class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({'class':'oh-input oh-calendar-input w-100'})
            elif isinstance(widget, (forms.NumberInput, forms.EmailInput,forms.TextInput)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label})
            elif isinstance(widget,(forms.Select,)):
                field.widget.attrs.update({'class': 'oh-select oh-select-2 select2-hidden-accessible'})
            elif isinstance(widget,(forms.Textarea)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label,'rows':2,'cols':40})
            elif isinstance(widget, (forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox'})


class ConditionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget,(forms.Select,)):
                field.widget.attrs['style'] = 'width:100%; height:50px;border: 1px solid hsl(213deg,22%,84%);border-radius: 0rem;padding: 0.8rem 1.25rem;'
            elif isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({'class':'oh-input oh-calendar-input w-100'})
            elif isinstance(widget, (forms.NumberInput, forms.EmailInput,forms.TextInput)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label})
            elif isinstance(widget,(forms.Textarea)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label,'rows':2,'cols':40})
            elif isinstance(widget, (forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox'})


class LeaveTypeForm(ConditionForm):
    require_approval = forms.CharField(
        label="Require Approval", widget=forms.RadioSelect(choices=CHOICES))
    exclude_company_leave = forms.CharField(
        label="Exclude Company Leave", widget=forms.RadioSelect(choices=CHOICES))
    exclude_holiday = forms.CharField(
        label="Exclude Holiday", widget=forms.RadioSelect(choices=CHOICES))
            
    class Meta:
        model = LeaveType
        fields = '__all__'
        labels = {
            'name':_('Name'),
        }
        widgets = {
            'color': TextInput(attrs={'type': 'color', 'style':'height:40px;'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if 'employee_id' in self.errors:
            del self.errors['employee_id']
        if 'exceed_days' in self.errors:
            del self.errors['exceed_days']
        return cleaned_data
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class UpdateLeaveTypeForm(ConditionForm):
    require_approval = forms.CharField(
        label="Require Approval", widget=forms.RadioSelect(choices=CHOICES))
    exclude_company_leave = forms.CharField(
        label="Exclude Company Leave", widget=forms.RadioSelect(choices=CHOICES))
    exclude_holiday = forms.CharField(
        label="Exclude Holiday", widget=forms.RadioSelect(choices=CHOICES))

    def __init__(self, *args, **kwargs):
        super(UpdateLeaveTypeForm, self).__init__(*args, **kwargs)

        empty_fields = []
        for field_name, field_value in self.instance.__dict__.items():
            if field_value is None or field_value == '':
                if field_name.endswith('_id'):
                    foreign_key_field_name = re.sub('_id$', '', field_name)
                    empty_fields.append(foreign_key_field_name)
                empty_fields.append(field_name)
  
        for index, visible in enumerate(self.visible_fields()):
            if list(self.fields.keys())[index] in empty_fields:
                visible.field.widget.attrs['style'] = 'display:none;width:100%; height:50px;border: 1px solid hsl(213deg,22%,84%);border-radius: 0rem;padding: 0.8rem 1.25rem;'
                visible.field.widget.attrs['data-hidden'] = True

    class Meta:
        model = LeaveType
        fields = '__all__'

        widgets = {
            'color': TextInput(attrs={'type': 'color', 'style':'height:40px;'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if 'exceed_days' in self.errors:
            del self.errors['exceed_days']
        return cleaned_data


class LeaveRequestCreationForm(ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee_id = cleaned_data.get('employee_id')
        leave_type_id = cleaned_data.get('leave_type_id')
        start_date_breakdown = cleaned_data.get('start_date_breakdown')
        end_date_breakdown = cleaned_data.get('end_date_breakdown')
        overlapping_requests = LeaveRequest.objects.filter(employee_id=employee_id,
            start_date__lte=end_date, end_date__gte=start_date
        )

        if not start_date <= end_date:
            raise forms.ValidationError(_("End date should not be less than start date."))
        
        if not AvailableLeave.objects.filter(employee_id=employee_id, leave_type_id=leave_type_id).exists():
            raise forms.ValidationError(_("Employee has no leave type.."))

        if overlapping_requests.exists():
            raise forms.ValidationError(_("Employee has already a leave request for this date range.."))
        
        available_leave = AvailableLeave.objects.get(employee_id=employee_id, leave_type_id=leave_type_id)
        total_leave_days = available_leave.available_days + available_leave.carryforward_days
        if start_date == end_date:
            if start_date_breakdown == 'full_day' and end_date_breakdown == 'full_day':
                requested_days = 1
            else:
                requested_days = 0.5
        else:
            start_days = 0
            end_days = 0   
            if start_date_breakdown != 'full_day':
                start_days = 0.5

            if end_date_breakdown != 'full_day':
                end_days = 0.5
            requested_days = (end_date - start_date).days + start_days + end_days - 1 
        if not requested_days <= total_leave_days:
            raise forms.ValidationError(_("Employee doesn't have enough leave days.."))


        return cleaned_data
    class Meta:
        model = LeaveRequest
        fields = ['leave_type_id', 'employee_id', 'start_date', 'start_date_breakdown','end_date','end_date_breakdown', 'description', 'attachment']


class LeaveRequestUpdationForm(ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee_id = cleaned_data.get('employee_id')
        leave_type_id = cleaned_data.get('leave_type_id')

        if not start_date <= end_date:
            raise forms.ValidationError(_("End date should not be less than start date."))
        
        if not AvailableLeave.objects.filter(employee_id=employee_id, leave_type_id=leave_type_id).exists():
            raise forms.ValidationError(_("Employee has no leave type.."))
        
        available_leave = AvailableLeave.objects.get(employee_id=employee_id, leave_type_id=leave_type_id)
        total_leave_days = available_leave.available_days + available_leave.carryforward_days
        requested_days = (end_date - start_date).days +  1
        
        if not requested_days <= total_leave_days:
            raise forms.ValidationError(_("Employee doesn't have enough leave days.."))

        return cleaned_data
    class Meta:
        model = LeaveRequest
        fields = ['leave_type_id', 'employee_id', 'start_date', 'start_date_breakdown','end_date','end_date_breakdown', 'description', 'attachment','status']
      


class AvailableLeaveForm(ModelForm):
    leave_type_id = forms.ModelChoiceField(
        queryset=LeaveType.objects.all(),
        widget=forms.SelectMultiple,
        empty_label=None,
    )
    employee_id = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple,
        empty_label=None,
    )

    class Meta:
        model = AvailableLeave
        fields = ['leave_type_id','employee_id']


class HolidayForm(ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                _('End date should not be earlier than the start date.'))

        return end_date

    class Meta:
        model = Holiday
        fields = '__all__'
        labels = {
            'name': _('Name'),
        }




class LeaveOneAssignForm(ModelForm):


    employee_id = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple,
        empty_label=None,
    )

    class Meta:
        model = AvailableLeave
        fields = ['employee_id']


    


class AvailableLeaveUpdateForm(ModelForm):

    class Meta:
        model = AvailableLeave
        fields = ['available_days', 'carryforward_days']
      


class CompanyLeaveForm(ModelForm):
    class Meta:
        model = CompanyLeave
        fields = "__all__"


class UserLeaveRequestForm(ModelForm):

    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(label=_('Description'), widget=forms.Textarea)
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if not start_date <= end_date:
            raise forms.ValidationError(_("End date should not be less than start date."))

        return cleaned_data

    def __init__(self,  *args, employee=None, **kwargs):
        super(UserLeaveRequestForm, self).__init__(*args, **kwargs)
        

    class Meta:
        model = LeaveRequest
        fields = ['start_date','start_date_breakdown','end_date','end_date_breakdown','description', 'attachment']
 
  
