"""
select_widgets.py

This module is used to write horilla form select widgets
"""
from django import forms


class HorillaMultiSelectWidget(forms.Widget):
    """
    HorillaMultiSelectWidget
    """

    def __init__(
        self,
        *args,
        filter_route_name,
        filter_class=None,
        filter_instance_contex_name=None,
        filter_template_path=None,
        instance=None,
        **kwargs
    ) -> None:
        self.filter_route_name = filter_route_name
        self.filter_class = filter_class
        self.filter_instance_contex_name = filter_instance_contex_name
        self.filter_template_path = filter_template_path
        self.instance = instance
        super().__init__()

    template_name = "horilla_widgets/horilla_multiselect_widget.html"

    def get_context(self, name, value, attrs):
        # Get the default context from the parent class
        context = super().get_context(name, value, attrs)
        # Add your custom data to the context
        queryset = self.choices.queryset
        field = self.choices.field
        context["queryset"] = queryset
        context["field_name"] = name
        context["field"] = field
        context["self"] = self
        context["filter_template_path"] = self.filter_template_path
        context["filter_route_name"] = self.filter_route_name
        self.attrs["id"] = ("id_" + name ) if self.attrs.get('id') is None else self.attrs.get("id")
        context[self.filter_instance_contex_name] = self.filter_class
        if self.instance is not None:
            data = getattr(self.instance,field)
            print(data)
        return context

    def value_from_datadict(self, data, files, name):
        print(data)
        print('---------------------')
        pass


"""
Attendance form field updations
"""

# def clean(self) -> Dict[str, Any]:
#         self.instance.employee_id = Employee.objects.filter(
#             id=self.data.get("employee_id")
#         ).first()

#         self.errors.pop("employee_id", None)
#         if self.instance.employee_id is None:
#             raise ValidationError({"employee_id": "This field is required"})
#         super().clean()
#         employee_ids = self.data.getlist("employee_id")
#         existing_attendance = Attendance.objects.filter(
#             attendance_date=self.data["attendance_date"]
#         ).filter(employee_id__id__in=employee_ids)
#         if existing_attendance.exists():
#             raise ValidationError(
#                 {
#                     "employee_id": f"""Already attendance exists for {list(existing_attendance.values_list("employee_id__employee_first_name",flat=True))} employees"""
#                 }
#             )


# class AttendanceForm(ModelForm):
#     """
#     Model form for Attendance model
#     """

#     employee_id = HorillaMultiSelectField(
#         queryset=Employee.objects.filter(employee_work_info__isnull=False),
#         widget=HorillaMultiSelectWidget(
#             filter_route_name="employee-widget-filter",
#             filter_class=EmployeeFilter,
#             filter_instance_contex_name="f",
#             filter_template_path="employee_filters.html",
#         ),
#         label=_("Employees"),
#     )