"""
accessibility/filters.py
"""

from functools import reduce

import django_filters
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from employee.models import Employee
from horilla.filters import HorillaFilterSet
from horilla.horilla_middlewares import _thread_locals


def _filter_form_structured(self):
    """
    Render the form fields as HTML table rows with Bootstrap styling.
    """
    request = getattr(_thread_locals, "request", None)
    context = {
        "form": self,
        "request": request,
    }
    table_html = render_to_string("accessibility/filter_form_body.html", context)
    return table_html


class AccessibilityFilter(HorillaFilterSet):
    """
    Accessibility Filter with dynamic OR logic between fields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.structured = _filter_form_structured(self.form)

    pk = django_filters.ModelMultipleChoiceFilter(
        queryset=Employee.objects.all(),
        field_name="pk",
        lookup_expr="in",
        label=_("Employee"),
    )
    exluded_employees = django_filters.ModelMultipleChoiceFilter(
        queryset=Employee.objects.all(),
        label=_("Exclude Employees"),
    )

    verbose_name = {
        "employee_work_info__job_position_id": _("Job Position"),
        "employee_work_info__department_id": _("Department"),
        "employee_work_info__work_type_id": _("Work Type"),
        "employee_work_info__employee_type_id": _("Employee Type"),
        "employee_work_info__job_role_id": _("Job Role"),
        "employee_work_info__company_id": _("Company"),
        "employee_work_info__shift_id": _("Shift"),
        "employee_work_info__tags": _("Tags"),
        "employee_user_id__groups": _("Groups"),
        "employee_user_id__user_permissions": _("Permissions"),
    }

    class Meta:
        """
        Meta class for additional options
        """

        model = Employee
        fields = [
            "pk",
            "employee_work_info__job_position_id",
            "employee_work_info__department_id",
            "employee_work_info__work_type_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__job_role_id",
            "employee_work_info__company_id",
            "employee_work_info__shift_id",
            "employee_work_info__tags",
            "employee_user_id__groups",
            "employee_user_id__user_permissions",
        ]

    def filter_queryset(self, queryset):
        """
        Dynamically apply OR condition between all specified fields
        """
        or_conditions = []

        # Get the filter fields from Meta class
        for field in self.Meta.fields:
            field_value = self.data.get(field)
            if field_value:
                if isinstance(field_value, list) and len(field_value) == 1:
                    field_value = field_value[0]

                if "__" in field:
                    or_conditions.append(Q(**{f"{field}__id__in": [field_value]}))
                else:
                    if isinstance(field_value, list):
                        or_conditions.append(Q(**{f"{field}__in": field_value}))
                    else:
                        or_conditions.append(Q(**{f"{field}__in": [field_value]}))

        if or_conditions:
            queryset = queryset.filter(reduce(lambda x, y: x | y, or_conditions))

        excluded_employees = self.data.get("exluded_employees")
        if excluded_employees:
            queryset = queryset.exclude(pk__in=excluded_employees)
        return queryset
