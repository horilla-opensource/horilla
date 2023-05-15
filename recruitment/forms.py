from django import forms
from django import forms
from .models import Stage, Recruitment, Candidate,  StageNote
import uuid
from employee.models import Employee
from django.utils.translation import gettext_lazy as _

class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput)):
                field.widget.attrs.update(
                    {'class': 'oh-input w-100', 'placeholder': field.label})
            elif isinstance(widget, forms.URLInput):
                field.widget.attrs.update(
                    {'class': 'oh-input w-100', 'placeholder': field.label})
            elif isinstance(widget, (forms.Select,)):
                label = field.label.replace('id', ' ')
                field.empty_label = f'---Choose {label}---'
                self.fields[field_name].widget.attrs.update(
                    {'id': uuid.uuid4, 'class': 'oh-select oh-select-2 w-100', 'style': 'height:50px;'})
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {'class': 'oh-input w-100', 'placeholder': field.label, 'rows': 2, 'cols': 40})
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox '})


class RegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select,)):
                label = ''
                if field.label is not None:
                    label = field.label.replace('id', ' ')
                field.empty_label = f'---Choose {label}---'
                self.fields[field_name].widget.attrs.update(
                    {'id': uuid.uuid4, 'class': 'oh-select-2 oh-select--sm w-100'})
            elif isinstance(widget, (forms.TextInput)):
                field.widget.attrs.update({'class': 'oh-input w-100', })
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox '})



class DropDownForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput, forms.URLInput)):
                field.widget.attrs.update(
                    {'class': 'oh-input oh-input--small oh-table__add-new-row d-block w-100', 'placeholder': field.label})
            elif isinstance(widget, (forms.Select,)):
                #     label = field.label.replace('id','')
                #     field.empty_label = f'---Choose {label}---'
                self.fields[field_name].widget.attrs.update(
                    {'class': 'oh-select-2 oh-select--xs-forced ', 'id': uuid.uuid4(), })
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {'class': 'oh-input oh-input--small oh-input--textarea', 'placeholder': field.label, 'rows': 1, 'cols': 40})
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({'class': 'oh-switch__checkbox '})
          

class RecruitmentCreationForm(ModelForm):
    class Meta:
        model = Recruitment
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'description': _('Description'),
            'vacancy': _('Vacancy')
        }
    def __init__(self, *args, **kwargs):
        super(RecruitmentCreationForm, self).__init__(*args, **kwargs)
        


class StageCreationForm(ModelForm):
    class Meta:
        model = Stage
        fields = '__all__'
        exclude = ('sequence',)
        labels = {
            'stage': _('Stage'),
            
        }

    def __init__(self, *args, **kwargs):
        super(StageCreationForm, self).__init__(*args, **kwargs)
        


class CandidateCreationForm(ModelForm):
    class Meta:
        model = Candidate
        fields = '__all__'
        exclude = ('confirmation', 'scheduled_for',
                   'schedule_date', 'joining_date', 'stage_id')        
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'name': _('Name'),
            'email': _('Email'),
            'mobile': _('Mobile'),
            'address': _('Address'),
            'zip': _('Zip'),
        }
    

    def save(self, commit: bool = ...):
        candidate = self.instance
        recruitment = candidate.recruitment_id
        stage = candidate.stage_id
        candidate.hired = False
        candidate.start_onboard = False
        if stage is not None:
            if stage.stage_type == 'hired' and candidate.canceled is False:
                candidate.hired = True
                candidate.start_onboard = True
        candidate.recruitment_id = recruitment
        candidate.stage_id = stage
        return super().save(commit)


class ApplicationForm(RegistrationForm):
    active_recruitment =  Recruitment.objects.filter(is_active=True,closed=False)
    recruitment_id = forms.ModelChoiceField(queryset=active_recruitment)
    class Meta:
        model = Candidate
        exclude = (
            'stage_id',
            'schedule_date',
            'referral',
            'start_onboard',
            'hired',
            'is_active',
            'canceled',
            'joining_date',
        )
        widgets = {
            'recruitment_id':forms.TextInput(attrs={'required':'required',}),
            'dob':forms.DateInput(attrs={'type':'date',})
        }
    def __init__(self, *args, **kwargs):
        super(ApplicationForm, self).__init__(*args, **kwargs)
        
class RecruitmentDropDownForm(DropDownForm):
    class Meta:
        fields = '__all__'
        model = Recruitment
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'description': _('Description'),
            'vacancy': _('Vacancy')
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_position_id'].widget.attrs.update({'id':uuid.uuid4})
        self.fields['recruitment_managers'].widget.attrs.update({'id':uuid.uuid4})

        field = self.fields['is_active']
        field.widget = field.hidden_widget()

    

class CandidateDropDownForm(DropDownForm):
    profile = forms.FileField(required=False)
    class Meta:
        model = Candidate
        fields = [
            'name','email','mobile','resume','stage_id','recruitment_id','profile'
        ]
        labels = {
            'name': _('Name'),
            'email': _('Email'),
            'mobile': _('Mobile'),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recruitment_id'].widget.attrs.update({'id':uuid.uuid4})
        self.fields['stage_id'].widget.attrs.update({'id':uuid.uuid4})

class StageDropDownForm(DropDownForm):
    class Meta:
        model = Stage
        fields = '__all__'
        exclude =['sequence',]
        labels = {
            'stage': _('Stage'),
        }

    def __init__(self, *args, **kwargs):
        super(StageDropDownForm, self).__init__(*args, **kwargs)
        stage = Stage.objects.last()
        if stage is not None and stage.sequence is not None:
            self.instance.sequence = stage.sequence + 1
        else:
            self.instance.sequence = 1



class StageNoteForm(ModelForm):
    class Meta:
        model = StageNote
        exclude = (
            'updated_by',
            'stage_id',
            )
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['candidate_id']
        field.widget = field.hidden_widget()



            
