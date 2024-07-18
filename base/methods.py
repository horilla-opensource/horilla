import io
import json
import os
import random
from datetime import date, datetime, time

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import F, ForeignKey, ManyToManyField, OneToOneField
from django.db.models.functions import Lower
from django.forms.models import ModelChoiceField
from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
from django.utils.translation import gettext as _
from xhtml2pdf import pisa

from base.models import Company, DynamicPagination
from employee.models import Employee, EmployeeWorkInformation
from horilla.decorators import login_required
from leave.models import LeaveRequest, LeaveRequestConditionApproval
from recruitment.models import Candidate


def filtersubordinates(request, queryset, perm=None, field=None):
    """
    This method is used to filter out subordinates queryset element.
    """
    user = request.user
    if user.has_perm(perm):
        return queryset

    manager = Employee.objects.filter(employee_user_id=user).first()

    if field:
        filter_expression = f"{field}__employee_work_info__reporting_manager_id"
        queryset = queryset.filter(**{filter_expression: manager})
        return queryset

    queryset = queryset.filter(
        employee_id__employee_work_info__reporting_manager_id=manager
    )
    return queryset


def filter_own_records(request, queryset, perm=None):
    """
    This method is used to filter out subordinates queryset element.
    """
    user = request.user
    if user.has_perm(perm):
        return queryset
    queryset = queryset.filter(employee_id=request.user.employee_get)
    return queryset


def filter_own_and_subordinate_recordes(request, queryset, perm=None):
    """
    This method is used to filter out subordinates queryset along with own queryset element.
    """
    user = request.user
    if user.has_perm(perm):
        return queryset
    queryset = filter_own_records(request, queryset, perm) | filtersubordinates(
        request, queryset, perm
    )
    return queryset


def filtersubordinatesemployeemodel(request, queryset, perm=None):
    """
    This method is used to filter out subordinates queryset element.
    """
    user = request.user
    if user.has_perm(perm):
        return queryset
    manager = Employee.objects.filter(employee_user_id=user).first()
    queryset = queryset.filter(employee_work_info__reporting_manager_id=manager)
    return queryset


def is_reportingmanager(request):
    """
    This method is used to check weather the employee is reporting manager or not.
    """
    try:
        user = request.user
        return user.employee_get.reporting_manager.all().exists()
    except:
        return False


def choosesubordinates(
    request,
    form,
    perm,
):
    user = request.user
    if user.has_perm(perm):
        return form
    manager = Employee.objects.filter(employee_user_id=user).first()
    queryset = Employee.objects.filter(employee_work_info__reporting_manager_id=manager)
    form.fields["employee_id"].queryset = queryset
    return form


def choosesubordinatesemployeemodel(request, form, perm):
    user = request.user
    if user.has_perm(perm):
        return form
    manager = Employee.objects.filter(employee_user_id=user).first()
    queryset = Employee.objects.filter(employee_work_info__reporting_manager_id=manager)

    form.fields["employee_id"].queryset = queryset
    return form


orderingList = [
    {
        "id": "",
        "field": "",
        "ordering": "",
    }
]


def sortby(request, queryset, key):
    """
    This method is used to sort query set by asc or desc
    """
    global orderingList
    id = request.user.id
    # here will create dictionary object to the global orderingList if not exists,
    # if exists then method will switch corresponding object ordering.
    filtered_list = [x for x in orderingList if x["id"] == id]
    ordering = filtered_list[0] if filtered_list else None
    if ordering is None:
        ordering = {
            "id": id,
            "field": None,
            "ordering": "-",
        }
        orderingList.append(ordering)
    sortby = request.GET.get(key)
    sort_count = request.GET.getlist(key).count(sortby)
    order = None
    if sortby is not None and sortby != "":

        field_parts = sortby.split("__")

        model_meta = queryset.model._meta

        # here will update the orderingList
        ordering["field"] = sortby
        if sort_count % 2 == 0:
            ordering["ordering"] = "-"
            order = sortby
        else:
            ordering["ordering"] = ""
            order = f"-{sortby}"

        for part in field_parts:
            field = model_meta.get_field(part)
            if isinstance(field, models.ForeignKey):
                model_meta = field.related_model._meta
            else:
                if isinstance(field, models.CharField):
                    queryset = queryset.annotate(lower_title=Lower(sortby))
                    queryset = queryset.order_by(f"{ordering['ordering']}lower_title")
                else:
                    queryset = queryset.order_by(f'{ordering["ordering"]}{sortby}')

        orderingList = [item for item in orderingList if item["id"] != id]
        orderingList.append(ordering)
    setattr(request, "sort_option", {})
    request.sort_option["order"] = order

    return queryset


def random_color_generator():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    if r == g or g == b or b == r:
        random_color_generator()
    return f"rgba({r}, {g}, {b} , 0.7)"


# color_palette=[]
# Function to generate distinct colors for each object
def generate_colors(num_colors):
    # Define a color palette with distinct colors
    color_palette = [
        "rgba(255, 99, 132, 1)",  # Red
        "rgba(54, 162, 235, 1)",  # Blue
        "rgba(255, 206, 86, 1)",  # Yellow
        "rgba(75, 192, 192, 1)",  # Green
        "rgba(153, 102, 255, 1)",  # Purple
        "rgba(255, 159, 64, 1)",  # Orange
    ]

    if num_colors > len(color_palette):
        for i in range(num_colors - len(color_palette)):
            color_palette.append(random_color_generator())

    colors = []
    for i in range(num_colors):
        # color=random_color_generator()
        colors.append(color_palette[i % len(color_palette)])

    return colors


def get_key_instances(model, data_dict):
    # Get all the models in the Django project
    all_models = apps.get_models()

    # Initialize a list to store related models include the function argument model as foreignkey
    related_models = []

    # Iterate through all models
    for other_model in all_models:
        # Iterate through fields of the model
        for field in other_model._meta.fields:
            # Check if the field is a ForeignKey and related to the function argument model
            if isinstance(field, ForeignKey) and field.related_model == model:
                related_models.append(other_model)
                break

    # Iterate through related models to filter instances
    for related_model in related_models:
        # Get all fields of the related model
        related_model_fields = related_model._meta.get_fields()

        # Iterate through fields to find ForeignKey fields
        for field in related_model_fields:
            if isinstance(field, ForeignKey):
                # Get the related name and field name
                related_name = field.related_query_name()
                field_name = field.name

                # Check if the related name exists in data_dict
                if related_name in data_dict:
                    # Get the related_id from data_dict
                    related_id_list = data_dict[related_name]
                    related_id = int(related_id_list[0])

                    # Filter instances based on the field and related_id
                    filtered_instance = related_model.objects.filter(
                        **{field_name: related_id}
                    ).first()

                    # Store the filtered instance back in data_dict
                    data_dict[related_name] = [str(filtered_instance)]

    # Get all the fields in the argument model
    model_fields = model._meta.get_fields()
    foreign_key_field_names = [
        field.name
        for field in model_fields
        if isinstance(field, ForeignKey or OneToOneField)
    ]
    # Create a list of field names that are present in data_dict
    present_foreign_key_field_names = [
        key for key in foreign_key_field_names if key in data_dict
    ]

    for field_name in present_foreign_key_field_names:
        try:
            # Get the list of integer values from data_dict for the field
            field_values = [int(value) for value in data_dict[field_name]]

            # Get the related model of the ForeignKey field
            related_model = model._meta.get_field(field_name).remote_field.model

            # Get the instances of the related model using the field values
            related_instances = related_model.objects.filter(id__in=field_values)

            # Create a list of string representations of the instances
            related_strings = [str(instance) for instance in related_instances]

            # Update data_dict with the list of string representations
            data_dict[field_name] = related_strings
        except (ObjectDoesNotExist, ValueError):
            pass

    # Create a list of field names that are ManyToManyField
    many_to_many_field_names = [
        field.name for field in model_fields if isinstance(field, ManyToManyField)
    ]
    # Create a list of field names that are present in data_dict for ManyToManyFields
    present_many_to_many_field_names = [
        key for key in many_to_many_field_names if key in data_dict
    ]

    for field_name in present_many_to_many_field_names:
        try:
            # Get the related model of the ManyToMany field
            related_model = model._meta.get_field(field_name).remote_field.model
            # Get a list of integer values from data_dict for the field
            field_values = [int(value) for value in data_dict[field_name]]

            # Filter instances of the related model based on the field values
            related_instances = related_model.objects.filter(id__in=field_values)

            # Update data_dict with the string representations of related instances
            data_dict[field_name] = [str(instance) for instance in related_instances]
        except (ObjectDoesNotExist, ValueError):
            pass

    nested_fields = [
        key
        for key in data_dict
        if "__" in key and not key.endswith("gte") and not key.endswith("lte")
    ]
    for key in nested_fields:
        field_names = key.split("__")
        field_values = data_dict[key]
        if (
            field_values != ["unknown"]
            and field_values != ["true"]
            and field_values != ["false"]
        ):
            nested_instance = get_nested_instances(model, field_names, field_values)
            if nested_instance is not None:
                data_dict[key] = nested_instance

    if "id" in data_dict:
        id = data_dict["id"][0]
        object = model.objects.filter(id=id).first()
        object = str(object)
        del data_dict["id"]
        data_dict["Object"] = [object]
    keys_to_remove = [
        key
        for key, value in data_dict.items()
        if value == ["unknown"]
        or key
        in [
            "sortby",
            "orderby",
            "view",
            "page",
            "group_by",
            "target",
            "rpage",
            "instances_ids",
            "asset_list",
            "vpage",
            "opage",
            "click_id",
            "csrfmiddlewaretoken",
            "assign_sortby",
            "request_sortby",
            "asset_under",
        ]
        or "dynamic_page" in key
    ]
    if not "search" in data_dict:
        if "search_field" in data_dict:
            del data_dict["search_field"]

    for key in keys_to_remove:
        del data_dict[key]
    return data_dict


def get_nested_instances(model, field_names, field_values):
    try:
        related_model = model
        for field_name in field_names:
            try:
                related_field = related_model._meta.get_field(field_name)
            except:
                pass
            try:
                related_model = related_field.remote_field.model
            except:
                pass
        object_ids = [int(value) for value in field_values if value != "not_set"]
        related_instances = related_model.objects.filter(id__in=object_ids)
        result = [str(instance) for instance in related_instances]
        if "not_set" in field_values:
            result.insert(0, "not_set")
        return result
    except (ObjectDoesNotExist, ValueError):
        return None


def closest_numbers(numbers: list, input_number: int) -> tuple:
    """
    This method is used to find previous and next of numbers
    """
    previous_number = input_number
    next_number = input_number
    try:
        index = numbers.index(input_number)
        if index > 0:
            previous_number = numbers[index - 1]
        else:
            previous_number = numbers[-1]
        if index + 1 == len(numbers):
            next_number = numbers[0]
        elif index < len(numbers):
            next_number = numbers[index + 1]
        else:
            next_number = numbers[0]
    except:
        pass
    return (previous_number, next_number)


@login_required
def export_data(request, model, form_class, filter_class, file_name):
    fields_mapping = {
        "male": _("Male"),
        "female": _("Female"),
        "other": _("Other"),
        "draft": _("Draft"),
        "active": _("Active"),
        "expired": _("Expired"),
        "terminated": _("Terminated"),
        "weekly": _("Weekly"),
        "monthly": _("Monthly"),
        "after": _("After"),
        "semi_monthly": _("Semi-Monthly"),
        "hourly": _("Hourly"),
        "daily": _("Daily"),
        "monthly": _("Monthly"),
        "full_day": _("Full Day"),
        "first_half": _("First Half"),
        "second_half": _("Second Half"),
        "requested": _("Requested"),
        "approved": _("Approved"),
        "cancelled": _("Cancelled"),
        "rejected": _("Rejected"),
        "cancelled_and_rejected": _("Cancelled & Rejected"),
        "late_come": _("Late Come"),
        "early_out": _("Early Out"),
    }

    selected_columns = []
    today_date = date.today().strftime("%Y-%m-%d")
    file_name = f"{file_name}_{today_date}.xlsx"
    data_export = {}

    form = form_class()
    model_fields = model._meta.get_fields()
    export_objects = filter_class(request.GET).qs
    selected_fields = request.GET.getlist("selected_fields")

    if not selected_fields:
        selected_fields = form.fields["selected_fields"].initial
        ids = request.GET.get("ids")
        id_list = json.loads(ids)
        export_objects = model.objects.filter(id__in=id_list)

    for field in form.fields["selected_fields"].choices:
        value = field[0]
        key = field[1]
        if value in selected_fields:
            selected_columns.append((value, key))

    for field_name, verbose_name in selected_columns:
        if field_name in selected_fields:
            data_export[verbose_name] = []
            for obj in export_objects:
                value = obj
                nested_attributes = field_name.split("__")
                for attr in nested_attributes:
                    value = getattr(value, attr, None)
                    if value is None:
                        break
                if value is True:
                    value = _("Yes")
                elif value is False:
                    value = _("No")
                if value in fields_mapping:
                    value = fields_mapping[value]
                if value == "None":
                    value = " "
                if field_name == "month":
                    value = _(value.title())

                # Check if the type of 'value' is time
                if isinstance(value, time):
                    user = request.user
                    employee = user.employee_get

                    # Taking the company_name of the user
                    info = EmployeeWorkInformation.objects.filter(employee_id=employee)
                    if info.exists():
                        for data in info:
                            employee_company = data.company_id
                        company_name = Company.objects.filter(id=employee_company.id)
                        emp_company = company_name.first()
                        # Access the date_format attribute directly
                        time_format = (
                            emp_company.time_format if emp_company else "hh:mm A"
                        )
                    else:
                        time_format = "hh:mm A"

                    time_formats = {
                        "hh:mm A": "%I:%M %p",  # 12-hour format
                        "HH:mm": "%H:%M",  # 24-hour format
                    }

                    # Convert the string to a datetime.time object
                    check_in_time = datetime.strptime(
                        str(value).split(".")[0], "%H:%M:%S"
                    ).time()

                    # Print the formatted time for each format
                    for format_name, format_string in time_formats.items():
                        if format_name == time_format:
                            value = check_in_time.strftime(format_string)

                # Check if the type of 'value' is date
                if type(value) == date:
                    user = request.user
                    employee = user.employee_get

                    # Taking the company_name of the user
                    info = EmployeeWorkInformation.objects.filter(employee_id=employee)
                    if info.exists():
                        for data in info:
                            employee_company = data.company_id
                        company_name = Company.objects.filter(company=employee_company)
                        emp_company = company_name.first()

                        # Access the date_format attribute directly
                        date_format = (
                            emp_company.date_format if emp_company else "MMM. D, YYYY"
                        )
                    else:
                        date_format = "MMM. D, YYYY"
                    # Define date formats
                    date_formats = {
                        "DD-MM-YYYY": "%d-%m-%Y",
                        "DD.MM.YYYY": "%d.%m.%Y",
                        "DD/MM/YYYY": "%d/%m/%Y",
                        "MM/DD/YYYY": "%m/%d/%Y",
                        "YYYY-MM-DD": "%Y-%m-%d",
                        "YYYY/MM/DD": "%Y/%m/%d",
                        "MMMM D, YYYY": "%B %d, %Y",
                        "DD MMMM, YYYY": "%d %B, %Y",
                        "MMM. D, YYYY": "%b. %d, %Y",
                        "D MMM. YYYY": "%d %b. %Y",
                        "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
                    }

                    # Convert the string to a datetime.date object
                    start_date = datetime.strptime(str(value), "%Y-%m-%d").date()

                    # Print the formatted date for each format
                    for format_name, format_string in date_formats.items():
                        if format_name == date_format:
                            value = start_date.strftime(format_string)
                if isinstance(value, datetime):
                    value = str(value)
                data_export[verbose_name].append(value)

    data_frame = pd.DataFrame(data=data_export)
    styled_data_frame = data_frame.style.applymap(
        lambda x: "text-align: center", subset=pd.IndexSlice[:, :]
    )

    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'

    writer = pd.ExcelWriter(response, engine="xlsxwriter")
    styled_data_frame.to_excel(writer, index=False, sheet_name="Sheet1")
    worksheet = writer.sheets["Sheet1"]
    worksheet.set_column("A:Z", 18)
    writer.close()

    return response


def reload_queryset(fields):
    """
    This method is used to reload the querysets in the form
    """
    for k, v in fields.items():
        if isinstance(v, ModelChoiceField):
            if v.queryset.model == Employee:
                v.queryset = v.queryset.model.objects.filter(is_active=True)
            elif v.queryset.model == Candidate:
                v.queryset = v.queryset.model.objects.filter(is_active=True)
            else:
                v.queryset = v.queryset.model.objects.all()
    return


def check_manager(employee, instance):
    try:
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == employee
        return employee == instance.employee_id.employee_work_info.reporting_manager_id
    except:
        return False


def check_owner(employee, instance):
    try:
        if isinstance(instance, Employee):
            return employee == instance
        return employee == instance.employee_id
    except:
        return False


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    if not uri.startswith("/static"):
        return uri
    uri = "payroll/fonts/Poppins_Regular.ttf"
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]

        result = list(os.path.realpath(path) for path in result)
        path = result[0]

    else:
        sUrl = settings.STATIC_URL
        sRoot = settings.STATIC_ROOT
        mUrl = settings.MEDIA_URL
        mRoot = settings.MEDIA_ROOT

        if uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    if os.name == "nt":
        return uri

    if not os.path.isfile(path):
        raise RuntimeError("media URI must start with %s or %s" % (sUrl, mUrl))
    return path


def generate_pdf(template_path, context, path=True, title=None, html=True):
    template_path = template_path
    context_data = context
    title = (
        f"""{context_data.get("employee")}'s payslip for {context_data.get("range")}.pdf"""
        if not title
        else title
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename={title}"

    if html:
        html = template_path
    else:
        template = get_template(template_path)
        html = template.render(context_data)

    pisa_status = pisa.CreatePDF(
        html.encode("utf-8"),
        dest=response,
        link_callback=link_callback,
    )

    if pisa_status.err:
        return HttpResponse("We had some errors <pre>" + html + "</pre>")

    return response


def filter_conditional_leave_request(request):
    approval_manager = Employee.objects.filter(employee_user_id=request.user).first()
    leave_request_ids = []
    multiple_approval_requests = LeaveRequestConditionApproval.objects.filter(
        manager_id=approval_manager
    )
    for instance in multiple_approval_requests:
        if instance.sequence > 1:
            pre_sequence = instance.sequence - 1
            leave_request_id = instance.leave_request_id
            instance = LeaveRequestConditionApproval.objects.filter(
                leave_request_id=leave_request_id, sequence=pre_sequence
            ).first()
            if instance and instance.is_approved:
                leave_request_ids.append(instance.leave_request_id.id)
        else:
            leave_request_ids.append(instance.leave_request_id.id)
    return LeaveRequest.objects.filter(pk__in=leave_request_ids)


def get_pagination():
    from horilla.horilla_middlewares import _thread_locals

    request = getattr(_thread_locals, "request", None)
    user = request.user
    page = DynamicPagination.objects.filter(user_id=user).first()
    count = 50
    if page:
        count = page.pagination
    return count
