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


class LeaveTypeFilter(FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = LeaveType
        fields = {

            'payment': ['exact'],

        }


class AssignedLeavefilter(FilterSet):
    leave_type = filters.CharFilter(
        field_name='leave_type_id__name', lookup_expr='icontains')
    employee_id = filters.CharFilter(
        field_name='employee_id__employee_first_name', lookup_expr='icontains')
    assigned_date = DateFilter(
        field_name='assigned_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = AvailableLeave
        fields = {
            'leave_type_id': ['exact'],

        }


class LeaveRequestFilter(FilterSet):
    employee_id = filters.CharFilter(
        field_name='employee_id__employee_first_name', lookup_expr='icontains')
    from_date = DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    to_date = DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    start_date = DateFilter(
        field_name='start_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = DateFilter(
        field_name='end_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = LeaveRequest
        fields = {
            'leave_type_id': ['exact'],
            'status' : ['exact'],
        }


class HolidayFilter(FilterSet):
    name = filters.CharFilter(
        field_name='name', lookup_expr='icontains')
    from_date = DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    to_date = DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    start_date = DateFilter(
        field_name='start_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = DateFilter(
        field_name='end_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Holiday
        fields = {
            'recurring': ['exact'],
            
        }


class CompanyLeavefilter(FilterSet):
    name = filters.CharFilter(
        field_name='based_on_week_day', lookup_expr='icontains')
  
    class Meta:
        model = CompanyLeave
        fields = {
            'based_on_week': ['exact'],
            'based_on_week_day': ['exact'],   
        }


class userLeaveRequestFilter(FilterSet):
    leave_type = filters.CharFilter(
        field_name='leave_type_id__name', lookup_expr='icontains')
    from_date = DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    to_date = DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    start_date = DateFilter(
        field_name='start_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = DateFilter(
        field_name='end_date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = LeaveRequest
        fields = {
            'leave_type_id': ['exact'],
            'status' : ['exact'],
        }