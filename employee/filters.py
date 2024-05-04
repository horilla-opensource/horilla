"""
filters.py

This page is used to register filter for employee models

"""

import datetime
import uuid

import django
import django_filters
from django import forms
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext as _
from django_filters import CharFilter, DateFilter

from attendance.models import Attendance
from base.methods import reload_queryset
from base.models import WorkType
from employee.models import DisciplinaryAction, Employee, Policy
from horilla.filters import FilterSet, filter_by_name
from horilla_documents.models import Document


class EmployeeFilter(FilterSet):
    """
    Filter set class for Candidate model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method="filter_by_name")
    selected_search_field = django_filters.ChoiceFilter(
        label="Search Field",
        choices=[
            ("employee", _("Search in : Employee")),
            ("reporting_manager", _("Search in : Reporting manager")),
            ("department", _("Search in : Department")),
            ("job_position", _("Search in : Job Position")),
        ],
        method="filter_by_name_and_field",
        widget=forms.Select(
            attrs={
                "size": 4,
                "class": "oh-input__icon",
                "style": "border: none; overflow: hidden; display: flex; position: absolute; z-index: 999; margin-left:8%;",
                "onclick": "$('.filterButton')[0].click();",
            }
        ),
    )
    employee_first_name = django_filters.CharFilter(lookup_expr="icontains")
    employee_last_name = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="icontains")
    department = django_filters.CharFilter(
        field_name="employee_work_info__department_id__department",
        lookup_expr="icontains",
    )

    is_active = django_filters.ChoiceFilter(
        field_name="is_active",
        label="Is Active",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )
    working_today = django_filters.BooleanFilter(
        label="Working", method="get_working_today"
    )

    not_in_yet = django_filters.DateFilter(
        method="not_in_yet_func",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    not_out_yet = django_filters.DateFilter(
        method="not_out_yet_func",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Employee
        fields = [
            "employee_first_name",
            "employee_last_name",
            "email",
            "badge_id",
            "phone",
            "country",
            "gender",
            "is_active",
            "employee_work_info__job_position_id",
            "employee_work_info__department_id",
            "department",
            "employee_work_info__work_type_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__job_role_id",
            "employee_work_info__reporting_manager_id",
            "employee_work_info__company_id",
            "employee_work_info__shift_id",
            "employee_work_info__tags",
            "employee_user_id__groups",
            "employee_user_id__user_permissions",
        ]

    def not_in_yet_func(self, queryset, _, value):
        """
        The method to filter out the not check-in yet employees
        """

        # Getting the queryset for those employees dont have any attendance for the date
        # in value.

        queryset1 = queryset.exclude(
            employee_attendances__attendance_date=value,
        )
        queryset2 = queryset.filter(
            employee_attendances__attendance_date=value,
            employee_attendances__attendance_clock_out__isnull=False,
        )

        queryset = (queryset1 | queryset2).distinct()

        return queryset

    def not_out_yet_func(self, queryset, _, value):
        """
        The method to filter out the not check-in yet employees
        """

        # Getting the queryset for those employees dont have any attendance for the date
        # in value.
        queryset = queryset.filter(
            employee_attendances__attendance_date=value,
            employee_attendances__attendance_clock_out__isnull=True,
        )
        return queryset

    def filter_queryset(self, queryset):
        """
        Override the default filtering behavior to handle None option.
        """
        from django.db.models import Q

        data = self.form.cleaned_data
        not_set_dict = {}
        for key, value in data.items():
            if isinstance(value, (list, django.db.models.query.QuerySet)):
                if value and "not_set" in value:
                    not_set_dict[key] = value

        if not_set_dict:
            q_objects = Q()
            for key, values in not_set_dict.items():
                for value in values:
                    if value == "not_set":
                        q_objects |= Q(**{f"{key}__isnull": True})
                    else:
                        q_objects |= Q(**{key: value})
            return queryset.filter(q_objects)
        return super().filter_queryset(queryset)

        # Continue with the default behavior for other filters

    def get_working_today(self, queryset, _, value):
        today = datetime.datetime.now().date()
        yesterday = today - datetime.timedelta(days=1)

        working_employees = Attendance.objects.filter(
            attendance_date__gte=yesterday,
            attendance_date__lte=today,
            attendance_clock_out_date__isnull=True,
        ).values_list("employee_id", flat=True)
        if value:
            queryset = queryset.filter(id__in=working_employees)
        else:
            queryset = queryset.exclude(id__in=working_employees)
        return queryset

    def filter_by_name(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        filter_method = {
            "department": "employee_work_info__department_id__department__icontains",
            "job_position": "employee_work_info__job_position_id__job_position__icontains",
            "job_role": "employee_work_info__job_role_id__job_role__icontains",
            "shift": "employee_work_info__shift_id__employee_shift__icontains",
            "work_type": "employee_work_info__work_type_id__work_type__icontains",
            "company": "employee_work_info__company_id__company__icontains",
        }
        search_field = self.data.get("search_field")
        # Split the search value into first name and last name
        if not search_field:
            parts = value.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            # Filter the queryset by first name and last name
            if first_name and last_name:
                queryset = queryset.filter(
                    employee_first_name__icontains=first_name,
                    employee_last_name__icontains=last_name,
                )
            elif first_name:
                queryset = queryset.filter(employee_first_name__icontains=first_name)
            elif last_name:
                queryset = queryset.filter(employee_last_name__icontains=last_name)
        else:
            if search_field == "reporting_manager":
                parts = value.split()
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                if first_name and last_name:
                    queryset = queryset.filter(
                        employee_work_info__reporting_manager_id__employee_first_name__icontains=first_name,
                        employee_work_info__reporting_manager_id__employee_last_name__icontains=last_name,
                    )
                elif first_name:
                    queryset = queryset.filter(
                        employee_work_info__reporting_manager_id__employee_first_name__icontains=first_name
                    )
                elif last_name:
                    queryset = queryset.filter(
                        employee_work_info__reporting_manager_id__employee_last_name__icontains=last_name
                    )
            else:
                filter = filter_method.get(search_field)
                queryset = queryset.filter(**{filter: value})

        return queryset

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        self.form.fields["is_active"].initial = True
        self.form.fields["email"].widget.attrs["autocomplete"] = "email"
        self.form.fields["phone"].widget.attrs["autocomplete"] = "phone"
        self.form.fields["country"].widget.attrs["autocomplete"] = "country"
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"
        self.model_choice_filters = [
            filter
            for filter in self.filters.values()
            if isinstance(filter, django_filters.ModelMultipleChoiceFilter)
        ]
        for model_choice_filter in self.model_choice_filters:
            queryset = (
                model_choice_filter.queryset.filter(is_active=True)
                if model_choice_filter.queryset.model == Employee
                else model_choice_filter.queryset
            )
            choices = [
                ("not_set", _("Not Set")),
            ]
            choices.extend([(obj.id, str(obj)) for obj in queryset])

            self.form.fields[model_choice_filter.field_name] = (
                forms.MultipleChoiceField(
                    choices=choices,
                    required=False,
                    widget=forms.SelectMultiple(
                        attrs={
                            "class": "oh-select oh-select-2 select2-hidden-accessible",
                            "id": uuid.uuid4(),
                        }
                    ),
                )
            )


class EmployeeReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("employee_work_info__job_position_id", "Job Position"),
        ("employee_work_info__department_id", "Department"),
        ("employee_work_info__shift_id", "Shift"),
        ("employee_work_info__work_type_id", "Work Type"),
        ("employee_work_info__job_role_id", "Job Role"),
        ("employee_work_info__reporting_manager_id", "Reporting Manager"),
        ("employee_work_info__company_id", "Company"),
    ]


class PolicyFilter(FilterSet):
    """
    PolicyFilter filterset class
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Policy
        fields = "__all__"


class DocumentRequestFilter(FilterSet):
    """
    Custom filter for Document Requests.
    """

    search = CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = Document
        fields = [
            "employee_id",
            "document_request_id",
            "status",
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__is_active",
            "employee_id__gender",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]


class DisciplinaryActionFilter(FilterSet):
    """
    Custom filter for Disciplinary Action.

    """

    search = CharFilter(method=filter_by_name)

    start_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = DisciplinaryAction
        ordering = ["-id"]
        fields = [
            "employee_id",
            "action",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]
