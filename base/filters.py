import django_filters
from horilla.filters import FilterSet, filter_by_name
from django_filters import CharFilter
from django import forms
from base.models import ShiftRequest,WorkTypeRequest, RotatingShiftAssign, RotatingWorkTypeAssign





class ShiftRequestFilter(FilterSet):
    requested_date = django_filters.DateFilter(
        field_name='requested_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    requested_date__gte = django_filters.DateFilter(
        field_name='requested_date', 
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    requested_date__lte = django_filters.DateFilter(
        field_name='requested_date', 
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = CharFilter(method=filter_by_name)

    class Meta:
        fields = '__all__'
        model = ShiftRequest
        fields = [
            
            'employee_id',
            'requested_date',
            'previous_shift_id',
            'shift_id',
            'approved',
            'canceled',
            'employee_id__employee_first_name',
            'employee_id__employee_last_name',
            'employee_id__is_active',
            'employee_id__gender',
            'employee_id__employee_work_info__job_position_id',
            'employee_id__employee_work_info__department_id',
            'employee_id__employee_work_info__work_type_id',
            'employee_id__employee_work_info__employee_type_id',
            'employee_id__employee_work_info__job_role_id',
            'employee_id__employee_work_info__reporting_manager_id',
            'employee_id__employee_work_info__company_id',
            'employee_id__employee_work_info__shift_id',
        ]
    
        
    
    


class WorkTypeRequestFilter(FilterSet):
    requested_date = django_filters.DateFilter(
        field_name='requested_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    requested_date__gte = django_filters.DateFilter(
        field_name='requested_till', 
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    requested_date__lte = django_filters.DateFilter(
        field_name='requested_till', 
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = CharFilter(method=filter_by_name)
    
    class Meta:
        fields = '__all__'
        model = WorkTypeRequest
        fields = [
            
            'employee_id',
            'requested_date',
            'previous_work_type_id',
            'approved',
            'work_type_id',
            'canceled',
            'employee_id__employee_first_name',
            'employee_id__employee_last_name',
            'employee_id__is_active',
            'employee_id__gender',
            'employee_id__employee_work_info__job_position_id',
            'employee_id__employee_work_info__department_id',
            'employee_id__employee_work_info__work_type_id',
            'employee_id__employee_work_info__employee_type_id',
            'employee_id__employee_work_info__job_role_id',
            'employee_id__employee_work_info__reporting_manager_id',
            'employee_id__employee_work_info__company_id',
            'employee_id__employee_work_info__shift_id',
        ]
        
    
    

class RotatingShiftAssignFilters(FilterSet):
    search = CharFilter(method=filter_by_name)

    next_change_date = django_filters.DateFilter(
        field_name='next_change_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    start_date = django_filters.DateFilter(
        field_name='start_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    class Meta:
        fields = '__all__'
        model = RotatingShiftAssign
        fields = [
            'employee_id',
            'rotating_shift_id',
            'next_change_date',
            'start_date',
            'based_on',
            'rotate_after_day',
            'rotate_every_weekend',
            'rotate_every',
            'current_shift',
            'next_shift',
            'is_active',
            'employee_id__employee_work_info__job_position_id',
            'employee_id__employee_work_info__department_id',
            'employee_id__employee_work_info__work_type_id',
            'employee_id__employee_work_info__employee_type_id',
            'employee_id__employee_work_info__job_role_id',
            'employee_id__employee_work_info__reporting_manager_id',
            'employee_id__employee_work_info__company_id',
            'employee_id__employee_work_info__shift_id',
            
        ]



class RotatingWorkTypeAssignFilter(FilterSet):
    search = CharFilter(method=filter_by_name)

    next_change_date = django_filters.DateFilter(
        field_name='next_change_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    start_date = django_filters.DateFilter(
        field_name='start_date', 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    class Meta:
        fields = '__all__'
        model = RotatingWorkTypeAssign
        fields = [
            'employee_id',
            'rotating_work_type_id',
            'next_change_date',
            'start_date',
            'based_on',
            'rotate_after_day',
            'rotate_every_weekend',
            'rotate_every',
            'current_work_type',
            'next_work_type',
            'is_active',
            'employee_id__employee_work_info__job_position_id',
            'employee_id__employee_work_info__department_id',
            'employee_id__employee_work_info__work_type_id',
            'employee_id__employee_work_info__employee_type_id',
            'employee_id__employee_work_info__job_role_id',
            'employee_id__employee_work_info__reporting_manager_id',
            'employee_id__employee_work_info__company_id',
            'employee_id__employee_work_info__shift_id',
            
        ]