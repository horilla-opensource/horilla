"""
filters.py

This page is used to register filter for attendance models

"""
import django_filters
from django.forms import DateTimeInput
from django import forms
from horilla.filters import filter_by_name
from attendance.models import (
    Attendance,
    AttendanceOverTime,
    AttendanceLateComeEarlyOut,
    AttendanceActivity,
)


class FilterSet(django_filters.FilterSet):
    """
    Custom FilterSet class that applies specific CSS classes to filter
    widgets.

    The class applies CSS classes to different types of filter widgets,
    such as NumberInput, EmailInput, TextInput, Select, Textarea,
    CheckboxInput, CheckboxSelectMultiple, and ModelChoiceField. The
    CSS classes are applied to enhance the styling and behavior of the
    filter widgets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, _ in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(self.filters[field_name], DurationInSecondsFilter):
                filter_widget.field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": "00:00"}
                )
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                filter_widget.field.widget.attrs.update(
                    {"class": "oh-switch__checkbox"}
                )
            elif isinstance(widget, (forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )


class DurationInSecondsFilter(django_filters.CharFilter):
    """
    Custom CharFilter class that applies specific filter process.
    """

    def filter(self, qs, value):
        """
        FilterSet filter method

        Args:
            qs (self): FilterSet instance
            value (str): duration formated string

        Returns:
            qs: queryset object
        """
        if value:
            ftr = [3600, 60, 1]
            duration_sec = sum(a * b for a, b in zip(ftr, map(int, value.split(":"))))
            lookup = self.lookup_expr or "exact"
            return qs.filter(**{f"{self.field_name}__{lookup}": duration_sec})
        return qs


class AttendanceOverTimeFilter(FilterSet):
    """
    Filter set class for AttendanceOverTime model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method=filter_by_name)

    hour_account__gte = DurationInSecondsFilter(
        field_name="hour_account_second", lookup_expr="gte"
    )
    hour_account__lte = DurationInSecondsFilter(
        field_name="hour_account_second", lookup_expr="lte"
    )
    overtime__gte = DurationInSecondsFilter(
        field_name="overtime_second", lookup_expr="gte"
    )
    overtime__lte = DurationInSecondsFilter(
        field_name="overtime_second", lookup_expr="lte"
    )
    month = django_filters.CharFilter(field_name="month", lookup_expr="icontains")

    class Meta:
        """
        Meta class to add additional options
        """

        model = AttendanceOverTime
        fields = [
            "employee_id",
            "month",
            "overtime",
            "hour_account",
            "year",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__location",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__shift_id",
            "employee_id__employee_work_info__work_type_id",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)


class LateComeEarlyOutFilter(FilterSet):
    """
    LateComeEarlyOutFilter class
    """
    search = django_filters.CharFilter(method=filter_by_name)
    attendance_date__gte = django_filters.DateFilter(
        field_name="attendance_id__attendance_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    attendance_date__lte = django_filters.DateFilter(
        field_name="attendance_id__attendance_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    attendance_clock_in__lte = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="lte",
    )
    attendance_clock_in__gte = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="gte",
    )
    attendance_clock_out__gte = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="gte",
    )
    attendance_clock_out__lte = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="lte",
    )
    attendance_clock_in = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="exact",
    )
    attendance_clock_out = django_filters.TimeFilter(
        field_name="attendance_id__attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="exact",
    )
    attendance_date = django_filters.DateFilter(
        field_name="attendance_id__attendance_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    overtime_second__lte = DurationInSecondsFilter(
        field_name="attendance_id__overtime_second", lookup_expr="lte"
    )
    overtime_second__gte = DurationInSecondsFilter(
        field_name="attendance_id__overtime_second", lookup_expr="gte"
    )
    at_work_second__lte = DurationInSecondsFilter(
        field_name="attendance_id__at_work_second", lookup_expr="lte"
    )
    at_work_second__gte = DurationInSecondsFilter(
        field_name="attendance_id__at_work_second", lookup_expr="gte"
    )

    class Meta:
        """
        Meta class for additional options"""
        model = AttendanceLateComeEarlyOut
        fields = [
            "employee_id",
            "type",
            "attendance_id__minimum_hour",
            "attendance_id__attendance_worked_hour",
            "attendance_id__attendance_overtime_approve",
            "attendance_id__attendance_validated",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__location",
            "employee_id__employee_work_info__reporting_manager_id",
            "attendance_id__shift_id",
            "attendance_id__work_type_id",
            "attendance_date__gte",
            "attendance_date__lte",
            "attendance_clock_in__lte",
            "attendance_clock_in__gte",
            "attendance_clock_out__gte",
            "attendance_clock_out__lte",
            "attendance_clock_in",
            "attendance_clock_out",
            "attendance_date",
        ]


class AttendanceActivityFilter(FilterSet):
    """
    Filter set class for AttendanceActivity model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method=filter_by_name)

    attendance_date = django_filters.DateFilter(
        field_name="attendance_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    attendance_date_from = django_filters.DateFilter(
        field_name="attendance_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    attendance_date_till = django_filters.DateFilter(
        field_name="attendance_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    in_form = django_filters.DateFilter(
        field_name="clock_in",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "time"}),
    )
    out_form = django_filters.DateFilter(
        field_name="clock_out",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "time"}),
    )
    in_till = django_filters.DateFilter(
        field_name="clock_in",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "time"}),
    )
    out_till = django_filters.DateFilter(
        field_name="clock_out",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "time"}),
    )
    clock_in_date = django_filters.DateFilter(
        field_name="clock_in_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    clock_out_date = django_filters.DateFilter(
        field_name="clock_out_date", widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        """
        Meta class to add additional options
        """

        fields = [
            "employee_id",
            "attendance_date",
            "attendance_date_from",
            "attendance_date_till",
            "in_form",
            "in_till",
            "out_form",
            "shift_day",
            "out_till",
            "clock_in_date",
            "clock_out_date",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__location",
            "employee_id__employee_work_info__reporting_manager_id",
        ]
        model = AttendanceActivity


class AttendanceFilters(FilterSet):
    """
    Filter set class for Attendance model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method=filter_by_name)

    attendance_date__gte = django_filters.DateFilter(
        field_name="attendance_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    attendance_date__lte = django_filters.DateFilter(
        field_name="attendance_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    attendance_clock_in__lte = django_filters.TimeFilter(
        field_name="attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="lte",
    )
    attendance_clock_in__gte = django_filters.TimeFilter(
        field_name="attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="gte",
    )
    attendance_clock_out__gte = django_filters.TimeFilter(
        field_name="attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="gte",
    )
    attendance_clock_out__lte = django_filters.TimeFilter(
        field_name="attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
        lookup_expr="lte",
    )
    attendance_clock_in = django_filters.TimeFilter(
        field_name="attendance_clock_in",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    attendance_clock_out = django_filters.TimeFilter(
        field_name="attendance_clock_out",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    attendance_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    at_work_second__lte = DurationInSecondsFilter(
        field_name="at_work_second", lookup_expr="lte"
    )
    at_work_second__gte = DurationInSecondsFilter(
        field_name="at_work_second", lookup_expr="gte"
    )
    overtime_second__lte = DurationInSecondsFilter(
        field_name="overtime_second", lookup_expr="lte"
    )
    overtime_second__gte = DurationInSecondsFilter(
        field_name="overtime_second", lookup_expr="gte"
    )

    class Meta:
        """
        Meta class to add additional options
        """

        model = Attendance
        fields = [
            "employee_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__location",
            "employee_id__employee_work_info__reporting_manager_id",
            "attendance_date",
            "work_type_id",
            "shift_id",
            "minimum_hour",
            "attendance_validated",
            "attendance_clock_in",
            "attendance_clock_out",
            "at_work_second",
            "overtime_second",
            "late_come_early_out__type",
            "attendance_overtime_approve",
            "attendance_validated",
            "at_work_second__lte",
            "at_work_second__gte",
            "overtime_second__lte",
            "overtime_second__gte",
            "overtime_second",
        ]

        widgets = {
            "attendance_date": DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)


class LateComeEarlyOutReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("type", "Type"),
        ("attendance_id.attendance_date", "Attendance Date"),
        ("attendance_id.shift_id", "Shift"),
        ("attendance_id.work_type_id", "Work Type"),
        ("attendance_id.minimum_hour", "Minimum Hour"),
        ("attendance_id.employee_id.country", "Country"),
        (
            "attendance_id.employee_id.employee_work_info.reporting_manager_id",
            "Reporting Manager",
        ),
        ("attendance_id.employee_id.employee_work_info.department_id", "Department"),
        (
            "attendance_id.employee_id.employee_work_info.job_position_id",
            "Job Position",
        ),
        (
            "attendance_id.employee_id.employee_work_info.employee_type_id",
            "Employment Type",
        ),
        ("attendance_id.employee_id.employee_work_info.company_id", "Company"),
    ]


class AttendanceReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("attendance_date", "Attendance Date"),
        ("shift_id", "Shift"),
        ("work_type_id", "Work Type"),
        ("minimum_hour", "Minimum Hour"),
        ("employee_id.country", "Country"),
        ("employee_id.employee_work_info.reporting_manager_id", "Reporting Manager"),
        ("employee_id.employee_work_info.department_id", "Department"),
        ("employee_id.employee_work_info.job_position_id", "Job Position"),
        ("employee_id.employee_work_info.employee_type_id", "Employment Type"),
        ("employee_id.employee_work_info.company_id", "Company"),
    ]


class AttendanceOvertimeReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("month", "Month"),
        ("year", "Year"),
        ("employee_id.country", "Country"),
        ("employee_id.employee_work_info.reporting_manager_id", "Reporting Manager"),
        ("employee_id.employee_work_info.shift_id", "Shift"),
        ("employee_id.employee_work_info.work_type_id", "Work Type"),
        ("employee_id.employee_work_info.department_id", "Department"),
        ("employee_id.employee_work_info.job_position_id", "Job Position"),
        ("employee_id.employee_work_info.employee_type_id", "Employment Type"),
        ("employee_id.employee_work_info.company_id", "Company"),
    ]


class AttendanceActivityReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("attendance_date", "Attendance Date"),
        ("clock_in_date", "In Date"),
        ("clock_out_date", "Out Date"),
        ("shift_day", "Shift Day"),
        ("employee_id.country", "Country"),
        ("employee_id.employee_work_info.reporting_manager_id", "Reporting Manager"),
        ("employee_id.employee_work_info.shift_id", "Shift"),
        ("employee_id.employee_work_info.work_type_id", "Work Type"),
        ("employee_id.employee_work_info.department_id", "Department"),
        ("employee_id.employee_work_info.job_position_id", "Job Position"),
        ("employee_id.employee_work_info.employee_type_id", "Employment Type"),
        ("employee_id.employee_work_info.company_id", "Company"),
    ]
