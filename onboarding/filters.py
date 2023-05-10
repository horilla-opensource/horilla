from .models import *
from django import forms
from django_filters import FilterSet, DateFilter, filters

class FilterSet(FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)):
                filter_widget.field.widget.attrs.update(
                    {'class': 'oh-input w-100'})
            elif isinstance(widget, (forms.Select,)):
                filter_widget.field.widget.attrs.update(
                    {'class': 'oh-select oh-select-2 select2-hidden-accessible', })
            elif isinstance(widget, (forms.Textarea)):
                filter_widget.field.widget.attrs.update(
                    {'class': 'oh-input w-100'})
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,)):
                filter_widget.field.widget.attrs.update(
                    {'class': 'oh-switch__checkbox'})
            elif isinstance(widget, (forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update(
                    {'class': 'oh-select oh-select-2 select2-hidden-accessible', })



class CandidateFilter(FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Candidate
        fields = {

            

        }