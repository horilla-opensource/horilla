import django_filters
from django import forms
from django.db.models import Q
from django.utils.translation import gettext as _

from horilla.filters import FilterSet, HorillaFilterSet, filter_by_name

from .models import Employee, Project, Task, TimeSheet


class ProjectFilter(HorillaFilterSet):
    search = django_filters.CharFilter(method="filter_by_project")
    search_field = django_filters.CharFilter(method="search_in")

    class Meta:
        model = Project
        fields = [
            "title",
            "managers",
            "members",
            "status",
            "end_date",
            "start_date",
            "is_active",
        ]

    start_from = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Start From"),
    )
    end_till = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("End Till"),
    )

    def filter_by_project(self, queryset, _, value):
        if self.data.get("search_field"):
            return queryset
        queryset = queryset.filter(title__icontains=value)
        return queryset


class TaskFilter(FilterSet):
    search = django_filters.CharFilter(method="filter_by_task")
    task_managers = django_filters.ModelChoiceFilter(
        field_name="task_managers", queryset=Employee.objects.all()
    )
    end_till = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Task
        fields = [
            "title",
            "stage",
            "task_managers",
            "end_date",
            "status",
            "project",
        ]

    def filter_by_task(self, queryset, _, value):
        queryset = queryset.filter(title__icontains=value)
        return queryset


class TaskAllFilter(HorillaFilterSet):
    search = django_filters.CharFilter(method="filter_by_task")
    end_till = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("End Till"),
    )

    class Meta:
        model = Task
        fields = [
            "title",
            "project",
            "stage",
            "task_managers",
            "task_members",
            "end_date",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields["end_till"].label = (
            f"{self.Meta.model()._meta.get_field('end_date').verbose_name} Till"
        )

    def filter_by_task(self, queryset, _, value):
        queryset = queryset.filter(title__icontains=value)
        return queryset


class TimeSheetFilter(HorillaFilterSet):
    """
    Filter set class for Timesheet model
    """

    date = django_filters.DateFilter(
        field_name="date", widget=forms.DateInput(attrs={"type": "date"})
    )
    start_from = django_filters.DateFilter(
        field_name="date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_till = django_filters.DateFilter(
        field_name="date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    project = (
        django_filters.ModelChoiceFilter(
            field_name="project_id", queryset=Project.objects.all()
        ),
    )

    task = django_filters.ModelChoiceFilter(
        field_name="task_id", queryset=Task.objects.all()
    )
    search = django_filters.CharFilter(method="filter_by_employee")

    class Meta:
        """
        Meta class to add additional options
        """

        model = TimeSheet
        fields = [
            "employee_id",
            "project_id",
            "task_id",
            "date",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields["start_from"].label = _("Start Date From")
        self.form.fields["end_till"].label = _("End Date Till")

    def filter_by_employee(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """

        # Split the search value into first name and last name

        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Filter the queryset by first name and last name
        if first_name and last_name != "":
            queryset = queryset.filter(
                Q(employee_id__employee_first_name__icontains=first_name)
                | Q(employee_id__employee_last_name__icontains=last_name)
            )
        elif first_name:
            queryset = queryset.filter(
                Q(employee_id__employee_first_name__icontains=first_name)
                | Q(employee_id__employee_last_name__icontains=first_name)
            )
        elif last_name:
            queryset = queryset.filter(
                employee_id__employee_last_name__icontains=last_name
            )
        return queryset
