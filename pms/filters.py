"""
Module: filters.py

This module contains custom Django filters and filter sets for
the PMS (Performance Management System) app.
"""

import datetime
from datetime import timedelta

import django
import django_filters
from dateutil.relativedelta import relativedelta
from django import forms
from django.utils import timezone
from django_filters import DateFilter, DateFromToRangeFilter

from base.filters import FilterSet
from base.methods import reload_queryset
from horilla.filters import HorillaFilterSet
from pms.models import (
    AnonymousFeedback,
    BonusPointSetting,
    EmployeeBonusPoint,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    Meetings,
    Objective,
    Period,
    QuestionTemplate,
)


class DateRangeFilter(django_filters.Filter):
    """
    A custom Django filter for filtering querysets based on date ranges.

    This filter allows you to filter a queryset based on date ranges such as 'today',
    'yesterday', 'week', or 'month' in the 'created_at' field of model.
    """

    def filter(self, qs, value):
        if value:
            if value == "today":
                today = datetime.datetime.now().date()
                formatted_date = today.strftime("%Y-%m-%d")
                qs = qs.filter(created_at__startswith=formatted_date)

            if value == "yesterday":
                today = datetime.date.today()
                yesterday = today - datetime.timedelta(days=1)
                formatted_date = yesterday.strftime("%Y-%m-%d")
                qs = qs.filter(created_at__startswith=formatted_date)

            if value == "week":
                today = datetime.date.today()
                start_of_week = today - datetime.timedelta(days=today.weekday())
                end_of_week = start_of_week + datetime.timedelta(days=6)
                qs = qs.filter(created_at__range=[start_of_week, end_of_week])

            elif value == "month":
                today = datetime.date.today()
                start_of_month = datetime.date(today.year, today.month, 1)
                end_of_month = start_of_month + datetime.timedelta(days=31)
                qs = qs.filter(created_at__range=[start_of_month, end_of_month])

        return qs


class CustomFilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.form.fields)
        for field_name, field in self.form.fields.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})
            elif isinstance(widget, (forms.ModelChoiceField)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            if isinstance(field, django_filters.CharFilter):
                field.lookup_expr = "icontains"


class ActualObjectiveFilter(HorillaFilterSet):
    """
    ActualObjectiveFilter
    """

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = Objective
        fields = [
            "managers",
            "archive",
            "assignees",
            "duration",
            "employee_objective__key_result_id",
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(managers__employee_first_name__icontains=split)
                | queryset.filter(managers__employee_last_name__icontains=split)
                | queryset.filter(assignees__employee_first_name__icontains=split)
                | queryset.filter(assignees__employee_last_name__icontains=split)
                | queryset.filter(title__icontains=split)
            )
        return empty.distinct()


class ObjectiveFilter(CustomFilterSet):
    """
    Custom filter set for EmployeeObjective records.

    This filter set allows to filter EmployeeObjective records based on various criteria.
    """

    employee_objective = django_filters.CharFilter(field_name="id")
    employee_objective__key_result_id = django_filters.CharFilter(
        field_name="key_result_id"
    )
    employee_objective__progress_percentage = django_filters.CharFilter(
        field_name="progress_percentage"
    )
    managers = django_filters.CharFilter(field_name="objective_id__managers")
    search = django_filters.CharFilter(method="search_method")
    created_at_date_range = DateRangeFilter(field_name="created_at")
    created_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    updated_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = EmployeeObjective
        fields = [
            "objective",
            "status",
            "employee_id",
            "created_at",
            "start_date",
            "updated_at",
            "end_date",
            "archive",
            "objective_id",
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search in managers and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(objective_id__title__icontains=split)
                | queryset.filter(
                    objective_id__managers__employee_first_name__icontains=split
                )
                | queryset.filter(
                    objective_id__managers__employee_last_name__icontains=split
                )
            )
        return empty


DUE_DATE_CHOICES = [
    ("", "All"),
    ("overdue", "Overdue"),
    ("due_today", "Due Today"),
    ("due_this_week", "Due This Week"),
    ("due_this_month", "Due This Month"),
]


class FeedbackFilter(HorillaFilterSet):
    """
    Custom filter set for Feedback records.

    This filter set allows to filter Feedback records based on various criteria.
    """

    due_date_quick_filter = django_filters.ChoiceFilter(
        label="Quick Date",
        choices=DUE_DATE_CHOICES,
        method="filter_due_date",
        widget=forms.HiddenInput(),  # We'll trigger this via pills
    )
    offboarding_employees = django_filters.BooleanFilter(
        method="filter_offboarding_employees",
    )

    search = django_filters.CharFilter(method="search_method")
    review_cycle = django_filters.CharFilter(lookup_expr="icontains")
    created_at_date_range = DateRangeFilter(
        field_name="created_at",
        widget=django_filters.widgets.RangeWidget(
            attrs={"type": "date", "class": "oh-input w-100"}
        ),
    )
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    start_date_range = DateFromToRangeFilter(
        field_name="start_date",
        widget=django_filters.widgets.RangeWidget(
            attrs={"type": "date", "class": "oh-input w-100"}
        ),
    )
    end_date_range = DateFromToRangeFilter(
        field_name="end_date",
        widget=django_filters.widgets.RangeWidget(
            attrs={"type": "date", "class": "oh-input w-100"}
        ),
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = Feedback
        fields = [
            "manager_id",
            "employee_id",
            "colleague_id",
            "subordinate_id",
            "question_template_id",
            "status",
            "archive",
            "start_date",
            "end_date",
            "employee_key_results_id",
            "cyclic_feedback",
            "cyclic_feedback_days_count",
            "cyclic_feedback_period",
            "cyclic_next_start_date",
            "cyclic_next_end_date",
            "start_date_range",
            "end_date_range",
        ]

    def filter_due_date(self, queryset, name, value):
        """
        Filter due date
        """
        queryset = queryset.exclude(status__iexact="Closed")

        today = timezone.now().date()

        if value == "overdue":
            return queryset.filter(end_date__lt=today)
        elif value == "due_today":
            return queryset.filter(end_date=today)
        elif value == "due_this_week":
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return queryset.filter(end_date__range=(start_of_week, end_of_week))
        elif value == "due_this_month":
            first_day = today.replace(day=1)
            last_day = (first_day + relativedelta(months=1)) - timedelta(days=1)
            return queryset.filter(end_date__range=(first_day, last_day))
        return queryset

    def filter_offboarding_employees(self, queryset, name, value):
        """
        Filter offboarding employees
        """
        queryset = queryset.filter(
            employee_id__offboardingemployee__isnull=not value
        ) | queryset.filter(employee_id__resignationletter__isnull=not value)
        return queryset.distinct()

    def search_method(self, queryset, _, value: str):
        """
        Search Method
        """
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        qrst = queryset.none()
        if first_name and last_name:
            qrst = queryset.filter(
                employee_id__employee_first_name__icontains=first_name,
                employee_id__employee_last_name__icontains=last_name,
            ) | queryset.filter(review_cycle__icontains=value)
        elif first_name:
            qrst = queryset.filter(
                employee_id__employee_first_name__icontains=first_name
            ) | queryset.filter(review_cycle__icontains=value)
        elif last_name:
            qrst = queryset.filter(
                employee_id__employee_last_name__icontains=last_name
            ) | queryset.filter(review_cycle__icontains=value)
        return qrst.distinct()


class AnonymousFeedbackFilter(django_filters.FilterSet):
    """
    Custom filter set for AnonymousFeedback records.

    This filter set allows to filter AnonymousFeedback records based on various criteria.
    """

    created_at_date_range = DateRangeFilter(field_name="created_at")
    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = AnonymousFeedback
        fields = "__all__"


class KeyResultFilter(CustomFilterSet):
    """
    KeyResult Filter
    """

    due = django_filters.ChoiceFilter(
        method="filter_due_date",
        label="Due",
        choices=[
            ("due_today", "Due Today"),
            ("due_this_week", "Due This Week"),
            ("due_this_month", "Due This Month"),
            ("due_next_month", "Due Next Month"),
            ("overdue", "Overdue"),
        ],
    )

    kr_progress_percentage__gte = django_filters.NumberFilter(
        field_name="progress_percentage", lookup_expr="gte"
    )
    kr_progress_percentage__lte = django_filters.NumberFilter(
        field_name="progress_percentage", lookup_expr="lte"
    )

    kr_start_date_from = django_filters.CharFilter(
        lookup_expr="gte", field_name="start_date"
    )
    kr_start_date_till = django_filters.CharFilter(
        lookup_expr="lte", field_name="start_date"
    )
    kr_end_date_from = django_filters.CharFilter(
        lookup_expr="gte", field_name="end_date"
    )
    kr_end_date_till = django_filters.CharFilter(
        lookup_expr="lte", field_name="end_date"
    )

    def filter_due_date(self, queryset, name, value):
        """
        Filter due date
        """
        today = timezone.now().date()

        if value == "due_today":
            return queryset.filter(end_date=today)
        elif value == "due_this_week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return queryset.filter(end_date__range=(start, end))
        elif value == "due_this_month":
            start = today.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            return queryset.filter(end_date__range=(start, end))
        elif value == "due_next_month":
            start = (today + relativedelta(months=1)).replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            return queryset.filter(end_date__range=(start, end))
        elif value == "overdue":
            return queryset.filter(end_date__lt=today)

        return queryset

    class Meta:
        model = EmployeeKeyResult
        fields = "__all__"


class ActualKeyResultFilter(HorillaFilterSet):
    """
    Filter through KeyResult model
    """

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = KeyResult
        fields = ["progress_type", "target_value", "duration", "company_id"]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (queryset.filter(title__icontains=split))

        return empty.distinct()


class ObjectiveReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("employee_id", "Owner"),
        ("status", "Status"),
    ]


class EmployeeObjectiveFilter(HorillaFilterSet):
    """
    Filter through EmployeeObjective model
    """

    search = django_filters.CharFilter(method="search_method")
    start_date_from = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    start_date_till = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date_from = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date_till = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    kr_start_date_from = django_filters.DateFilter(
        method="kr_start_date_till_method",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    kr_start_date_till = django_filters.DateFilter(
        method="kr_start_date_till_method",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    kr_end_date_from = django_filters.DateFilter(
        method="kr_end_date_from_method",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    kr_end_date_till = django_filters.DateFilter(
        method="kr_end_date_till_method",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    due = django_filters.ChoiceFilter(
        method="filter_due_date",
        label="Due",
        choices=[
            ("due_today", "Due Today"),
            ("due_this_week", "Due This Week"),
            ("due_this_month", "Due This Month"),
            ("due_next_month", "Due Next Month"),
            ("overdue", "Overdue"),
        ],
    )
    progress_percentage__gte = django_filters.NumberFilter(
        field_name="progress_percentage", lookup_expr="gte"
    )
    progress_percentage__lte = django_filters.NumberFilter(
        field_name="progress_percentage", lookup_expr="lte"
    )
    kr_progress_percentage__gte = django_filters.NumberFilter(method="kr_progress_gte")
    kr_progress_percentage__lte = django_filters.NumberFilter(method="kr_progress_lte")

    def kr_start_date_from_method(self, queryset, name, value):
        """
        Kr filter
        """
        return queryset.filter(employee_key_result__start_date__gte=value)

    def kr_start_date_till_method(self, queryset, name, value):
        """
        Kr filter
        """
        return queryset.filter(employee_key_result__start_date__lte=value)

    def kr_end_date_from_method(self, queryset, name, value):
        """
        Kr filter
        """
        return queryset.filter(employee_key_result__end_date__gte=value)

    def kr_end_date_till_method(self, queryset, name, value):
        """
        Kr filter
        """
        return queryset.filter(employee_key_result__end_date__lte=value)

    def kr_progress_gte(self, queryset, name, value):
        """
        Kr prgress filter
        """
        return queryset.filter(employee_key_result__progress_percentage__gte=value)

    def kr_progress_lte(self, queryset, name, value):
        """
        Kr prgress filter
        """
        return queryset.filter(employee_key_result__progress_percentage__lte=value)

    def filter_due_date(self, queryset, name, value):
        """
        Filter due date
        """
        today = timezone.now().date()

        if value == "due_today":
            return queryset.filter(employee_key_result__end_date=today)
        elif value == "due_this_week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return queryset.filter(employee_key_result__end_date__range=(start, end))
        elif value == "due_this_month":
            start = today.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            return queryset.filter(employee_key_result__end_date__range=(start, end))
        elif value == "due_next_month":
            start = (today + relativedelta(months=1)).replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            return queryset.filter(employee_key_result__end_date__range=(start, end))
        elif value == "overdue":
            return queryset.filter(employee_key_result__end_date__lt=today)

        return queryset

    class Meta:
        model = EmployeeObjective
        fields = [
            "status",
            "archive",
            "key_result_id",
            "start_date",
            "end_date",
            "employee_id",
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = (
                empty
                | (queryset.filter(employee_id__employee_first_name__icontains=split))
                | (queryset.filter(employee_id__employee_last_name__icontains=split))
                | (queryset.filter(objective__icontains=split))
                | (queryset.filter(employee_key_result__key_result__icontains=split))
            )

        return empty.distinct()


class MeetingsFilter(HorillaFilterSet):

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    date = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_greater = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date__gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_less = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date__lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Meetings
        fields = [
            "employee_id",
            "manager",
            "question_template",
            "is_active",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__shift_id",
            "employee_id__employee_work_info__reporting_manager_id",
        ]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     queryset = self.filters["question_template"].queryset
    #     choices = [
    #         ("not_set", "Not Set"),
    #     ]
    #     choices.extend([(obj.id, str(obj)) for obj in queryset])
    #     self.form.fields["question_template"] = (
    #         forms.MultipleChoiceField(
    #             choices=choices,
    #             required=False,
    #             widget=forms.SelectMultiple(
    #                 attrs={
    #                     "class": "oh-select oh-select-2 select2-hidden-accessible",
    #                 }
    #             ),
    #         )
    #     )

    # def filter_queryset(self, queryset):
    #     """
    #     Override the default filtering behavior to handle None option.
    #     """
    #     from django.db.models import Q

    #     data = self.form.cleaned_data
    #     not_set_dict = {}
    #     for key, value in data.items():
    #         if isinstance(value, (list, django.db.models.query.QuerySet)):
    #             if value and "not_set" in value:
    #                 not_set_dict[key] = value

    #     if not_set_dict:
    #         q_objects = Q()
    #         for key, values in not_set_dict.items():
    #             for value in values:
    #                 if value == "not_set":
    #                     q_objects |= Q(**{f"{key}__isnull": True})
    #                 else:
    #                     q_objects |= Q(**{key: value})
    #         return queryset.filter(q_objects)
    #     return super().filter_queryset(queryset)


class AnonymousFilter(HorillaFilterSet):
    """
    Custom filter set for Anonymous records.

    This filter set allows to filter Anonymous records based on various criteria.
    """

    search = django_filters.CharFilter(method="search_method", lookup_expr="icontains")
    review_cycle = django_filters.CharFilter(lookup_expr="icontains")
    created_at_date_range = DateRangeFilter(field_name="created_at")
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    def filter(self, qs, value):
        if value:
            if value == "today":
                today = datetime.datetime.now().date()
                formatted_date = today.strftime("%Y-%m-%d")
                qs = qs.filter(created_at__startswith=formatted_date)

            if value == "yesterday":
                today = datetime.date.today()
                yesterday = today - datetime.timedelta(days=1)
                formatted_date = yesterday.strftime("%Y-%m-%d")
                qs = qs.filter(created_at__startswith=formatted_date)

            if value == "week":
                today = datetime.date.today()
                start_of_week = today - datetime.timedelta(days=today.weekday())
                end_of_week = start_of_week + datetime.timedelta(days=6)
                qs = qs.filter(created_at__range=[start_of_week, end_of_week])

            elif value == "month":
                today = datetime.date.today()
                start_of_month = datetime.date(today.year, today.month, 1)
                end_of_month = start_of_month + datetime.timedelta(days=31)
                qs = qs.filter(created_at__range=[start_of_month, end_of_month])

        return qs

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = AnonymousFeedback
        fields = "__all__"

    def search_method(self, queryset, _, value: str):
        """
        Search Method
        """
        return queryset.filter(feedback_subject__icontains=value)

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super(AnonymousFilter, self).__init__(
            data=data, queryset=queryset, request=request, prefix=prefix
        )


class QuestionTemplateFilter(FilterSet):

    search = django_filters.CharFilter(
        field_name="question_template", lookup_expr="icontains"
    )

    class Meta:
        model = QuestionTemplate
        fields = [
            "question_template",
        ]


class PeriodFilter(HorillaFilterSet):

    search = django_filters.CharFilter(
        field_name="period_name", lookup_expr="icontains"
    )

    class Meta:
        model = Period
        fields = [
            "period_name",
        ]


class BonusPointSettingFilter(FilterSet):
    """
    Filter through BonusPointSetting model
    """

    # search = django_filters.CharFilter(method="search_method")
    # start_date_from = django_filters.DateFilter(
    #     field_name="start_date",
    #     lookup_expr="gte",
    #     widget=forms.DateInput(attrs={"type": "date"}),
    # )
    # start_date_till = django_filters.DateFilter(
    #     field_name="start_date",
    #     lookup_expr="lte",
    #     widget=forms.DateInput(attrs={"type": "date"}),
    # )
    # end_date_from = django_filters.DateFilter(
    #     field_name="end_date",
    #     lookup_expr="gte",
    #     widget=forms.DateInput(attrs={"type": "date"}),
    # )
    # end_date_till = django_filters.DateFilter(
    #     field_name="end_date",
    #     lookup_expr="lte",
    #     widget=forms.DateInput(attrs={"type": "date"}),
    # )

    class Meta:
        model = BonusPointSetting
        fields = "__all__"

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = (
                empty
                | (queryset.filter(employee_id__employee_first_name__icontains=split))
                | (queryset.filter(employee_id__employee_last_name__icontains=split))
            )

        return empty.distinct()


class EmployeeBonusPointFilter(FilterSet):
    """
    Filter through BonusPointSetting model
    """

    class Meta:
        model = EmployeeBonusPoint
        fields = "__all__"

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = (
                empty
                | (queryset.filter(employee_id__employee_first_name__icontains=split))
                | (queryset.filter(employee_id__employee_last_name__icontains=split))
            )

        return empty.distinct()
