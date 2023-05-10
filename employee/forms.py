from django import forms
from django.contrib.auth.models import User
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails
from django.forms import DateInput,TextInput
from django.db import models
from django.core.exceptions import ValidationError
import json
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput,forms.TextInput)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label})
            elif isinstance(widget,(forms.Select,)):
                label = ''
                if field.label is not None:
                    label = field.label.replace('id','')
                field.empty_label = f'---Choose {label}---'
                field.widget.attrs.update({'class': 'oh-select oh-select-2 select2-hidden-accessible'})
            elif isinstance(widget,(forms.Textarea)):
                field.widget.attrs.update({'class': 'oh-input w-100','placeholder':field.label,'rows':2,'cols':40})
            elif isinstance(widget, (forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox'})
                

class UserForm(ModelForm):
    class Meta:
        fields = ('groups',)
        model = User

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        

class UserPermissionForm(ModelForm):
    class Meta:
        fields = ('groups','user_permissions')
        model = User

    def __init__(self, *args, **kwargs):
        super(UserPermissionForm, self).__init__(*args, **kwargs)
        

class EmployeeForm(ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        exclude = ('employee_user_id',)
        widgets = {
            'dob': TextInput(attrs={'type': 'date','id':'dob'}),

        }
    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        if instance := kwargs.get('instance'):
            '''
            django forms not showing value inside the date, time html element. 
            so here overriding default forms instance method to set initial value
            '''
            initial = {}
            if instance.dob is not None:
                    initial['dob'] = instance.dob.strftime('%H:%M')
            kwargs['initial']=initial
        else:
            self.initial = {"badge_id":self.get_next_badge_id()}

        for field in self.fields:            
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
        self.fields['employee_last_name'].required = False

        
    def get_next_badge_id(self):
        try:
            total_employee_count = Employee.objects.filter(~Q(badge_id=None)).count()
        except:
            total_employee_count = 0
        try:
            string = Employee.objects.filter(~Q(badge_id=None)).order_by('-id').last().badge_id
        except:
            string = "DUDE"
        # Find the index of the last integer group in the string
        integer_group_index = None
        for i in range(len(string) - 1, -1, -1):
            if string[i].isdigit():
                integer_group_index = i
            elif integer_group_index is not None:
                break

        if integer_group_index is None:
            # There is no integer group in the string, so just append #01
            return string + '#01'
        else:
            # Extract the integer group from the string
            integer_group = string[integer_group_index:]
            prefix = string[:integer_group_index]

            # Set the integer group to the total number of employees plus one
            new_integer_group = str(total_employee_count + 1).zfill(len(integer_group))

            # Return the new string
            return prefix + new_integer_group
        
    def clean_badge_id(self):
        badge_id = self.cleaned_data['badge_id']
        if badge_id:
            qs = Employee.objects.filter(badge_id=badge_id).exclude(pk=self.instance.pk if self.instance else None)
            if qs.exists():
                raise forms.ValidationError(_("Badge ID must be unique."))
        return badge_id
        
    
class EmployeeWorkInformationForm(ModelForm):
    employees =  Employee.objects.filter(employee_work_info=None)
    employee_id = forms.ModelChoiceField(queryset=employees)
    class Meta:
        model = EmployeeWorkInformation
        fields = '__all__'
        widgets = {
            'date_joining': DateInput(attrs={'type': 'date'}),
            'contract_end_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args,disable=False, **kwargs):
        super(EmployeeWorkInformationForm, self).__init__(*args, **kwargs)
        for field in self.fields:            
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
            if disable:
                self.fields[field].disabled = True
        

    def clean(self):
        cleaned_data = super().clean()
        if 'employee_id' in self.errors:
            del self.errors['employee_id']
        


class EmployeeWorkInformationUpdateForm(ModelForm):
    class Meta:
        model = EmployeeWorkInformation
        fields = '__all__'
        exclude = ('employee_id',)

        widgets = {
            'date_joining': DateInput(attrs={'type': 'date'}),
            'contract_end_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(EmployeeWorkInformationUpdateForm, self).__init__(*args, **kwargs)
    

class EmployeeBankDetailsForm(ModelForm):
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}))

    class Meta:
        model = EmployeeBankDetails
        fields = '__all__'
        exclude = ['employee_id',]
    def __init__(self, *args, **kwargs):
        super(EmployeeBankDetailsForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'oh-input w-100'
        for field in self.fields:            
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
        
        # self.fields['reporting_manager_id'].widget.attrs.update({'class': 'oh-select oh-select-2 select2-hidden-accessible'})

        
class EmployeeBankDetailsUpdateForm(ModelForm):
    class Meta:
        model = EmployeeBankDetails
        fields = '__all__'
        exclude = ('employee_id',)

    def __init__(self, *args, **kwargs):
        super(EmployeeBankDetailsUpdateForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'oh-input w-100'
        for field in self.fields:            
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label

class EmployeeProfileBankDetailsForm(ModelForm):
    class Meta:
        model = EmployeeBankDetails
        fields = '__all__'
        exclude = ('employee_id',)

    def __init__(self, *args, **kwargs):
        super(EmployeeProfileBankDetailsForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'oh-input w-100'
