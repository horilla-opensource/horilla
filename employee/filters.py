"""
filters.py

This page is used to register filter for employee models

"""

import django
import django_filters
from django import forms
from django.utils.translation import gettext as _
from django_filters import CharFilter

# from attendance.models import Attendance
from accessibility.models import DefaultAccessibility
from employee.models import DisciplinaryAction, Employee, Policy
from horilla.filters import FilterSet, HorillaFilterSet, filter_by_name
from horilla.horilla_middlewares import _thread_locals
from horilla_documents.models import Document
from horilla_views.templatetags.generic_template_filters import getattribute


class EmployeeFilter(HorillaFilterSet):
    """
    Filter set class for Candidate model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method="filter_by_name")
    search_field = django_filters.CharFilter(method="search_in")
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

    is_from_onboarding = django_filters.ChoiceFilter(
        field_name="is_from_onboarding",
        label="Is From Onboarding",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )
    is_directly_converted = django_filters.ChoiceFilter(
        field_name="is_directly_converted",
        label="Is Directly Converted",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )
    probation_from = django_filters.DateFilter(
        field_name="candidate_get__probation_end",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_till = django_filters.DateFilter(
        field_name="candidate_get__probation_end",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
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
        Override the default filtering behavior to handle None option and filter queryset for reporting manager.
        """
        from django.db.models import Q

        # Handle default accessibility and filter based on reporting manager
        accessibility = DefaultAccessibility.objects.filter(
            feature="employee_view"
        ).first()
        if accessibility and accessibility.exclude_all:
            request = getattr(_thread_locals, "request", None)
            employee = getattr(request.user, "employee_get", None)
            if employee and employee.reporting_manager.exists():
                queryset = queryset.filter(
                    employee_work_info__reporting_manager_id=employee
                )

        # Handle 'not_set' values in the cleaned data
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

    def filter_by_name(self, queryset, name, value):
        """
        Employee search method
        """
        value = value.lower()

        if self.data.get("search_field"):
            return queryset

        def _icontains(instance):
            result = str(getattribute(instance, "get_full_name")).lower()
            return instance.pk if value in result else None

        ids = list(filter(None, map(_icontains, queryset)))
        return queryset.filter(id__in=ids)


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
