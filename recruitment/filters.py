import django_filters
from django import forms

from recruitment.models import Candidate, Recruitment, Stage
from django import forms
# from django.forms.widgets import Boo  

from django.db  import models

class FilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput,forms.TextInput)):
                filter_widget.field.widget.attrs.update({'class': 'oh-input w-100'})
            elif isinstance(widget,(forms.Select,)):
                filter_widget.field.widget.attrs.update({'class': 'oh-select oh-select-2 select2-hidden-accessible',})
            elif isinstance(widget,(forms.Textarea)):
                filter_widget.field.widget.attrs.update({'class': 'oh-input w-100'})
            elif isinstance(widget, (forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                filter_widget.field.widget.attrs.update({'class': 'oh-switch__checkbox'})
            elif isinstance(widget,(forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update({'class': 'oh-select oh-select-2 select2-hidden-accessible',})




class CandidateFilter(FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains'
    )
    start_date = django_filters.DateFilter(
        field_name='recruitment_id__start_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = django_filters.DateFilter(
        field_name='recruitment_id__end_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    scheduled_from = django_filters.DateFilter(
        field_name='schedule_date', 
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    scheduled_till = django_filters.DateFilter(
        field_name='schedule_date', 
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    class Meta:
        model = Candidate
        fields=[
            'recruitment_id',
            'stage_id',
            'schedule_date',
            'email',
            'mobile',
            'country',
            'state',
            'city',
            'zip',
            'gender',
            'start_onboard',
            'hired',
            'canceled',
            'is_active',
            'recruitment_id__company_id',
            'recruitment_id__job_position_id',
            'recruitment_id__closed',
            'recruitment_id__is_active',
            'recruitment_id__job_position_id__department_id',
            'recruitment_id__recruitment_managers',
            'stage_id__stage_managers',
            'stage_id__stage_type',
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields['is_active'].initial = True
        


BOOLEAN_CHOICES = (('',''),('false', 'False'), ('true', 'True'),)


class RecruitmentFilter(FilterSet):
    description = django_filters.CharFilter(lookup_expr='icontains')
    start_date = django_filters.DateFilter(
        field_name='start_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = django_filters.DateFilter(
        field_name='end_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    start_from = django_filters.DateFilter(
        field_name='start_date', 
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_till = django_filters.DateFilter(
        field_name='end_date', 
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = django_filters.CharFilter(method='filter_by_name')
    
    class Meta:
        model = Recruitment
        fields = [
            'recruitment_managers',
            'company_id',
            'start_date',
            'end_date',
            'closed',
            'is_active',
            'job_position_id',            
        ]

    
    def filter_by_name(self,queryset, name, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        # Filter the queryset by first name and last name
        job_queryset = queryset.filter(job_position_id__job_position__icontains = value)
        if first_name and last_name:
            queryset = queryset.filter(recruitment_managers__employee_first_name__icontains=first_name, recruitment_managers__employee_last_name__icontains=last_name)
        elif first_name:
            queryset = queryset.filter(recruitment_managers__employee_first_name__icontains=first_name)
        elif last_name:
            queryset = queryset.filter(recruitment_managers__employee_last_name__icontains=last_name)

        return queryset | job_queryset


class StageFilter(FilterSet):
    search = django_filters.CharFilter(method='filter_by_name')

    class Meta:
        model = Stage
        fields = [
            'recruitment_id',
            'recruitment_id__job_position_id',
            'recruitment_id__job_position_id__department_id',
            'recruitment_id__company_id',
            'recruitment_id__recruitment_managers',
            'stage_managers',
            'stage_type',
        ]
    def filter_by_name(self,queryset, name, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        # Filter the queryset by first name and last name
        stage_queryset = queryset.filter(stage__icontains = value)
        if first_name and last_name:
            queryset = queryset.filter(stage_managers__employee_first_name__icontains=first_name, stage_managers__employee_last_name__icontains=last_name)
        elif first_name:
            queryset = queryset.filter(stage_managers__employee_first_name__icontains=first_name)
        elif last_name:
            queryset = queryset.filter(stage_managers__employee_last_name__icontains=last_name)

        return queryset | stage_queryset
