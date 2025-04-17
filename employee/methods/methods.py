"""
employee/methods.py
"""

import logging
import re
import threading
from datetime import date, datetime
from itertools import groupby

import pandas as pd
from django.apps import apps
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext as _

from base.context_processors import get_initial_prefix
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeType,
    JobPosition,
    JobRole,
    WorkType,
)
from employee.models import Employee, EmployeeWorkInformation

logger = logging.getLogger(__name__)

error_data_template = {
    field: []
    for field in [
        "Badge ID",
        "First Name",
        "Last Name",
        "Phone",
        "Email",
        "Gender",
        "Department",
        "Job Position",
        "Job Role",
        "Work Type",
        "Shift",
        "Employee Type",
        "Reporting Manager",
        "Company",
        "Location",
        "Date Joining",
        "Contract End Date",
        "Basic Salary",
        "Salary Hour",
        "Email Error",
        "First Name Error",
        "Name and Email Error",
        "Phone Error",
        "Gender Error",
        "Joining Date Error",
        "Contract Date Error",
        "Badge ID Error",
        "Basic Salary Error",
        "Salary Hour Error",
        "User ID Error",
        "Company Error",
    ]
}


def normalize_phone(phone):
    phone = str(phone).strip()
    if phone.startswith("+"):
        return "+" + re.sub(r"\D", "", phone[1:])
    return re.sub(r"\D", "", phone)


def import_valid_date(date_value, field_label, errors_dict, error_key):
    if pd.isna(date_value) or date_value is None or str(date_value).strip() == "":
        return None

    if isinstance(date_value, datetime):
        return date_value.date()

    date_str = str(date_value).strip()
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    errors_dict[error_key] = (
        f"{field_label} is not a valid date. Expected formats: YYYY-MM-DD, DD/MM/YYYY"
    )
    return None


def convert_nan(field, dicts):
    """
    This method is returns None or field value
    """
    field_value = dicts.get(field)
    try:
        float(field_value)
        return None
    except ValueError:
        return field_value


def dynamic_prefix_sort(item):
    """
    Sorts items based on a dynamic prefix length.
    """
    # Assuming the dynamic prefix length is 3
    prefix = get_initial_prefix(None)["get_initial_prefix"]

    prefix_length = len(prefix) if len(prefix) >= 3 else 3
    return item[:prefix_length]


def get_ordered_badge_ids():
    """
    This method is used to return ordered badge ids
    """
    employees = Employee.objects.all()
    data = (
        employees.exclude(badge_id=None)
        .order_by("badge_id")
        .values_list("badge_id", flat=True)
    )
    if not data.first():
        data = [
            f'{get_initial_prefix(None)["get_initial_prefix"]}0001',
        ]
    # Separate pure number strings and convert them to integers
    pure_numbers = [int(item) for item in data if item.isdigit()]

    # Remove pure number strings from the original data
    data = [item for item in data if not item.isdigit()]

    # Sort the remaining data by dynamic prefixes
    sorted_data = sorted(data, key=dynamic_prefix_sort)

    # Group the sorted data by dynamic prefixes
    grouped_data = [
        list(group) for _, group in groupby(sorted_data, key=dynamic_prefix_sort)
    ]

    # Sort each subgroup alphabetically and numerically
    for group in grouped_data:
        group.sort()
        filtered_group = [
            item for item in group if any(char.isdigit() for char in item)
        ]
        filtered_group.sort(key=lambda x: int("".join(filter(str.isdigit, x))))

    # Create a list containing the first and last items from each group
    result = [[group[0], group[-1]] for group in grouped_data]

    # Add the list of pure numbers at the beginning
    if pure_numbers:
        result.insert(0, [pure_numbers[0], pure_numbers[-1]])
    return result


def check_relationship_with_employee_model(model):
    """
    Checks the relationship of a given model with the Employee model.

    This function iterates through all the fields of the specified model
    and identifies fields that are either `ForeignKey` or `ManyToManyField`
    and are related to the `Employee` model. For each such field, it adds
    the field name and the type of relationship to a list.
    """
    related_fields = []
    for field in model._meta.get_fields():
        # Check if the field is a ForeignKey or ManyToManyField and related to Employee
        if isinstance(field, models.ForeignKey) and field.related_model == Employee:
            related_fields.append((field.name, "ForeignKey"))
        elif (
            isinstance(field, models.ManyToManyField)
            and field.related_model == Employee
        ):
            related_fields.append((field.name, "ManyToManyField"))
    return related_fields


def valid_import_file_headers(data_frame):
    if data_frame.empty:
        message = _("The uploaded file is empty, Not contain records.")
        return False, message

    required_keys = [
        "Badge ID",
        "First Name",
        "Last Name",
        "Phone",
        "Email",
        "Gender",
        "Department",
        "Job Position",
        "Job Role",
        "Work Type",
        "Shift",
        "Employee Type",
        "Reporting Manager",
        "Company",
        "Location",
        "Date Joining",
        "Contract End Date",
        "Basic Salary",
        "Salary Hour",
    ]

    missing_keys = [key for key in required_keys if key not in data_frame.columns]
    if missing_keys:
        message = _(
            "These required headers are missing in the uploaded file: "
        ) + ", ".join(missing_keys)
        return False, message
    return True, ""


def process_employee_records(data_frame):
    created_count = 0
    success_list, error_list = [], []
    employee_dicts = data_frame.to_dict("records")
    email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone_regex = re.compile(r"^\+?\d{10,15}$")
    allowed_genders = {choice[0] for choice in Employee.choice_gender}

    existing_badge_ids = set(Employee.objects.values_list("badge_id", flat=True))
    existing_usernames = set(User.objects.values_list("username", flat=True))
    existing_name_emails = set(
        Employee.objects.values_list(
            "employee_first_name", "employee_last_name", "email"
        )
    )
    existing_companies = set(Company.objects.values_list("company", flat=True))

    for emp in employee_dicts:
        errors, save = {}, True

        email = emp.get("Email", "").strip()
        raw_phone = emp.get("Phone", "")
        phone = normalize_phone(raw_phone)
        badge_id = str(emp.get("Badge ID", "") or "").strip()
        first_name = convert_nan("First Name", emp)
        last_name = convert_nan("Last Name", emp)
        gender = emp.get("Gender", "").strip().lower()
        company = convert_nan("Company", emp)
        basic_salary = convert_nan("Basic Salary", emp)
        salary_hour = convert_nan("Salary Hour", emp)

        joining_date = import_valid_date(
            emp.get("Date Joining"), "Joining Date", errors, "Joining Date Error"
        )
        if "Joining Date Error" in errors:
            save = False
        if joining_date and joining_date > date.today():
            errors["Joining Date Error"] = "Joining date cannot be in the future."
            save = False

        contract_end_date = import_valid_date(
            emp.get("Contract End Date"),
            "Contract End Date",
            errors,
            "Contract Date Error",
        )
        if "Contract Error" in errors:
            save = False
        if contract_end_date and joining_date and contract_end_date < joining_date:
            errors["Contract Date Error"] = (
                "Contract end date cannot be before joining date."
            )
            save = False

        if not email or not email_regex.match(email):
            errors["Email Error"] = "Invalid email address."
            save = False

        if not first_name:
            errors["First Name Error"] = "First name cannot be empty."
            save = False

        if not phone_regex.match(phone):
            errors["Phone Error"] = "Invalid phone number format."
            save = False

        if badge_id in existing_badge_ids:
            errors["Badge ID Error"] = "An employee with this badge ID already exists."
            save = False
        else:
            existing_badge_ids.add(badge_id)

        if email in existing_usernames:
            errors["User ID Error"] = "User with this email already exists."
            save = False
        else:
            existing_usernames.add(email)

        name_email_tuple = (first_name, last_name, email)
        if name_email_tuple in existing_name_emails:
            errors["Name and Email Error"] = (
                "This employee already exists in the system."
            )
            save = False
        else:
            existing_name_emails.add(name_email_tuple)

        if gender and gender not in allowed_genders:
            errors["Gender Error"] = (
                f"Invalid gender. Allowed values: {', '.join(allowed_genders)}."
            )
            save = False

        if company and company not in existing_companies:
            errors["Company Error"] = f"Company '{company}' does not exist."
            save = False

        if basic_salary not in [None, ""]:
            try:
                basic_salary_val = float(basic_salary)
                if basic_salary_val <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors["Basic Salary Error"] = "Basic salary must be a positive number."
                save = False

        if salary_hour not in [None, ""]:
            try:
                salary_hour_val = float(salary_hour)
                if salary_hour_val < 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors["Salary Hour Error"] = (
                    "Salary hour must be a non-negative number."
                )
                save = False

        if save:
            emp["Phone"] = phone
            emp["Date Joining"] = joining_date
            emp["Contract End Date"] = contract_end_date
            success_list.append(emp)
            created_count += 1
        else:
            emp.update(errors)
            error_list.append(emp)

    return success_list, error_list, created_count


def bulk_create_user_import(success_lists):
    """
    Bulk creation of user instances based on the excel import of employees
    """
    user_obj_list = []
    existing_usernames = {
        user.username
        for user in User.objects.filter(
            username__in=[row["Email"] for row in success_lists]
        )
    }

    for work_info in success_lists:
        email = work_info["Email"]
        if email in existing_usernames:
            continue

        phone = work_info["Phone"]
        user_obj = User(
            username=email,
            email=email,
            password=str(phone).strip(),
            is_superuser=False,
        )
        user_obj_list.append(user_obj)
    result = []
    if user_obj_list:
        result = User.objects.bulk_create(user_obj_list)
    return result


def bulk_create_employee_import(success_lists):
    """
    Bulk creation of employee instances based on the excel import of employees
    """
    employee_obj_list = []
    existing_users = {
        user.username: user
        for user in User.objects.filter(
            username__in=[row["Email"] for row in success_lists]
        )
    }

    for work_info in success_lists:
        email = work_info["Email"]
        user = existing_users.get(email)
        if not user:
            continue

        badge_id = work_info["Badge ID"]
        first_name = convert_nan("First Name", work_info)
        last_name = convert_nan("Last Name", work_info)
        phone = work_info["Phone"]
        gender = work_info.get("Gender", "").lower()
        employee_obj = Employee(
            employee_user_id=user,
            badge_id=badge_id,
            employee_first_name=first_name,
            employee_last_name=last_name,
            email=email,
            phone=phone,
            gender=gender,
        )
        employee_obj_list.append(employee_obj)
    result = []
    if employee_obj_list:
        result = Employee.objects.bulk_create(employee_obj_list)

    return result


def set_initial_password(employees):
    """
    method to set initial password
    """

    logger.info("started to set initial password")
    for employee in employees:
        try:
            employee.employee_user_id.set_password(str(employee.phone))
            employee.employee_user_id.save()
        except Exception as e:
            logger.error(f"falied to set initial password for {employee}")
    logger.info("initial password configured")


def optimize_reporting_manager_lookup():
    """
    Optimizes the lookup of reporting managers from a list of work information.

    This function identifies unique reporting manager names from the provided
    list of work information, queries all matching `Employee` objects in a
    single database query, and creates a dictionary for quick lookups based
    on the full name of the reporting managers.
    """
    employees = Employee.objects.entire()

    employee_dict = {
        f"{employee.employee_first_name} {employee.employee_last_name}": employee
        for employee in employees
    }
    return employee_dict


def bulk_create_department_import(success_lists):
    """
    Bulk creation of department instances based on the excel import of employees
    """
    departments_to_import = {
        convert_nan("Department", work_info) for work_info in success_lists
    }
    existing_departments = {dep.department for dep in Department.objects.all()}
    department_obj_list = []

    for department in departments_to_import:
        if department and department not in existing_departments:
            department_obj = Department(department=department)
            department_obj_list.append(department_obj)
            existing_departments.add(department)

    if department_obj_list:
        Department.objects.bulk_create(department_obj_list)


def bulk_create_job_position_import(success_lists):
    """
    Bulk creation of job position instances based on the excel import of employees
    """
    job_positions_to_import = {
        (convert_nan("Job Position", work_info), convert_nan("Department", work_info))
        for work_info in success_lists
    }
    departments = {dep.department: dep for dep in Department.objects.all()}
    existing_job_positions = {
        (job_position.job_position, job_position.department_id): job_position
        for job_position in JobPosition.objects.all()
    }
    job_position_obj_list = []
    for job_position, department_name in job_positions_to_import:
        if not job_position or not department_name:
            continue

        department_obj = departments.get(department_name)
        if not department_obj:
            continue

        # Check if this job position already exists for this department
        if (job_position, department_obj.id) not in existing_job_positions:
            job_position_obj = JobPosition(
                department_id=department_obj, job_position=job_position
            )
            job_position_obj_list.append(job_position_obj)
            existing_job_positions[(job_position, department_obj.id)] = job_position_obj

    if job_position_obj_list:
        JobPosition.objects.bulk_create(job_position_obj_list)


def bulk_create_job_role_import(success_lists):
    """
    Bulk creation of job role instances based on the excel import of employees
    """
    # Collect job role names and their associated job positions into a set as tubles
    job_roles_to_import = {
        (convert_nan("Job Role", work_info), convert_nan("Job Position", work_info))
        for work_info in success_lists
    }

    job_positions = {jp.job_position: jp for jp in JobPosition.objects.all()}
    existing_job_roles = {
        (jr.job_role, jr.job_position_id): jr for jr in JobRole.objects.all()
    }

    job_role_obj_list = []

    for job_role, job_position_name in job_roles_to_import:

        if not job_role or not job_position_name:
            continue

        job_position_obj = job_positions.get(job_position_name)
        if not job_position_obj:
            continue

        if (job_role, job_position_obj.id) not in existing_job_roles:
            job_role_obj = JobRole(job_position_id=job_position_obj, job_role=job_role)
            job_role_obj_list.append(job_role_obj)
            existing_job_roles[(job_role, job_position_obj.id)] = job_role_obj

    if job_role_obj_list:
        JobRole.objects.bulk_create(job_role_obj_list)


def bulk_create_work_types(success_lists):
    """
    Bulk creation of work type instances based on the excel import of employees
    """
    # Collect unique work types
    work_types_to_import = {
        convert_nan("Work Type", work_info) for work_info in success_lists
    }
    work_types_to_import.discard(None)

    # Fetch existing work types
    existing_work_types = {wt.work_type: wt for wt in WorkType.objects.all()}

    # Prepare list for new WorkType objects
    work_type_obj_list = [
        WorkType(work_type=work_type)
        for work_type in work_types_to_import
        if work_type not in existing_work_types
    ]
    # Bulk create new work types
    if work_type_obj_list:
        WorkType.objects.bulk_create(work_type_obj_list)


def bulk_create_shifts(success_lists):
    """
    Bulk creation of shift instances based on the excel import of employees
    """
    # Collect unique shifts
    shifts_to_import = {convert_nan("Shift", work_info) for work_info in success_lists}
    shifts_to_import.discard(None)

    # Fetch existing shifts
    existing_shifts = {
        shift.employee_shift: shift for shift in EmployeeShift.objects.all()
    }

    # Prepare list for new EmployeeShift objects
    shift_obj_list = [
        EmployeeShift(employee_shift=shift)
        for shift in shifts_to_import
        if shift not in existing_shifts
    ]
    # Bulk create new shifts
    if shift_obj_list:
        EmployeeShift.objects.bulk_create(shift_obj_list)


def bulk_create_employee_types(success_lists):
    """
    Bulk creation of employee type instances based on the excel import of employees
    """
    # Collect unique employee types
    employee_types_to_import = {
        convert_nan("Employee Type", work_info) for work_info in success_lists
    }
    employee_types_to_import.discard(None)

    # Fetch existing employee types
    existing_employee_types = {
        et.employee_type: et for et in EmployeeType.objects.all()
    }

    # Prepare list for new EmployeeType objects
    employee_type_obj_list = [
        EmployeeType(employee_type=employee_type)
        for employee_type in employee_types_to_import
        if employee_type not in existing_employee_types
    ]
    # Bulk create new employee types
    if employee_type_obj_list:
        EmployeeType.objects.bulk_create(employee_type_obj_list)


def create_contracts_in_thread(new_work_info_list, update_work_info_list):
    """
    Creates employee contracts in bulk based on provided work information.
    """
    from payroll.models.models import Contract

    def get_or_none(value):
        return value if value else None

    contracts_list = [
        Contract(
            contract_name=f"{work_info.employee_id}'s Contract",
            employee_id=work_info.employee_id,
            contract_start_date=(
                work_info.date_joining if work_info.date_joining else datetime.today()
            ),
            department=get_or_none(work_info.department_id),
            job_position=get_or_none(work_info.job_position_id),
            job_role=get_or_none(work_info.job_role_id),
            shift=get_or_none(work_info.shift_id),
            work_type=get_or_none(work_info.work_type_id),
            wage=work_info.basic_salary or 0,
        )
        for work_info in new_work_info_list + update_work_info_list
        if work_info.employee_id
    ]

    Contract.objects.bulk_create(contracts_list)


def bulk_create_work_info_import(success_lists):
    """
    Bulk creation of employee work info instances based on the excel import of employees
    """
    new_work_info_list = []
    update_work_info_list = []

    badge_ids = [row["Badge ID"] for row in success_lists]
    departments = set(row.get("Department") for row in success_lists)
    job_positions = set(row.get("Job Position") for row in success_lists)
    job_roles = set(row.get("Job Role") for row in success_lists)
    work_types = set(row.get("Work Type") for row in success_lists)
    employee_types = set(row.get("Employee Type") for row in success_lists)
    shifts = set(row.get("Shift") for row in success_lists)
    companies = set(row.get("Company") for row in success_lists)

    existing_employees = {
        emp.badge_id: emp
        for emp in Employee.objects.entire()
        .filter(badge_id__in=badge_ids)
        .only("badge_id")
    }
    existing_employee_work_infos = {
        emp.employee_id: emp
        for emp in EmployeeWorkInformation.objects.filter(
            employee_id__in=existing_employees.values()
        ).only("employee_id")
    }
    existing_departments = {
        dep.department: dep
        for dep in Department.objects.filter(department__in=departments).only(
            "department"
        )
    }
    existing_job_positions = {
        (jp.department_id, jp.job_position): jp
        for jp in JobPosition.objects.filter(job_position__in=job_positions)
        .select_related("department_id")
        .only("department_id", "job_position")
    }
    existing_job_roles = {
        (jr.job_position_id, jr.job_role): jr
        for jr in JobRole.objects.filter(job_role__in=job_roles)
        .select_related("job_position_id")
        .only("job_position_id", "job_role")
    }
    existing_work_types = {
        wt.work_type: wt
        for wt in WorkType.objects.filter(work_type__in=work_types).only("work_type")
    }
    existing_shifts = {
        es.employee_shift: es
        for es in EmployeeShift.objects.filter(employee_shift__in=shifts).only(
            "employee_shift"
        )
    }
    existing_employee_types = {
        et.employee_type: et
        for et in EmployeeType.objects.filter(employee_type__in=employee_types).only(
            "employee_type"
        )
    }
    existing_companies = {
        comp.company: comp
        for comp in Company.objects.filter(company__in=companies).only("company")
    }
    reporting_manager_dict = optimize_reporting_manager_lookup()

    for work_info in success_lists:
        email = work_info["Email"]
        badge_id = work_info["Badge ID"]
        department_obj = existing_departments.get(work_info.get("Department"))

        job_position_key = (
            existing_departments.get(work_info.get("Department")),
            work_info.get("Job Position"),
        )
        job_position_obj = existing_job_positions.get(job_position_key)

        job_role_key = (
            job_position_obj,
            work_info.get("Job Role"),
        )
        job_role_obj = existing_job_roles.get(job_role_key)

        work_type_obj = existing_work_types.get(work_info.get("Work Type"))
        employee_type_obj = existing_employee_types.get(work_info.get("Employee Type"))
        shift_obj = existing_shifts.get(work_info.get("Shift"))
        reporting_manager = work_info.get("Reporting Manager")
        reporting_manager_obj = None
        if isinstance(reporting_manager, str) and " " in reporting_manager:
            if reporting_manager in reporting_manager_dict:
                reporting_manager_obj = reporting_manager_dict[reporting_manager]

        company_obj = existing_companies.get(work_info.get("Company"))
        location = work_info.get("Location")

        # Parsing dates and salary
        date_joining = (
            work_info["Date Joining"]
            if not pd.isnull(work_info["Date Joining"])
            else datetime.today()
        )

        contract_end_date = (
            work_info["Contract End Date"]
            if not pd.isnull(work_info["Contract End Date"])
            else None
        )
        basic_salary = (
            convert_nan("Basic Salary", work_info)
            if type(convert_nan("Basic Salary", work_info)) is int
            else 0
        )
        salary_hour = (
            convert_nan("Salary Hour", work_info)
            if type(convert_nan("Salary Hour", work_info)) is int
            else 0
        )

        employee_obj = existing_employees.get(badge_id)
        employee_work_info = existing_employee_work_infos.get(employee_obj)

        if employee_work_info is None:
            # Create a new instance
            employee_work_info = EmployeeWorkInformation(
                employee_id=employee_obj,
                email=email,
                department_id=department_obj,
                job_position_id=job_position_obj,
                job_role_id=job_role_obj,
                work_type_id=work_type_obj,
                employee_type_id=employee_type_obj,
                shift_id=shift_obj,
                reporting_manager_id=reporting_manager_obj,
                company_id=company_obj,
                location=location,
                date_joining=(
                    date_joining if not pd.isnull(date_joining) else datetime.today()
                ),
                contract_end_date=(
                    contract_end_date if not pd.isnull(contract_end_date) else None
                ),
                basic_salary=basic_salary,
                salary_hour=salary_hour,
            )
            new_work_info_list.append(employee_work_info)
        else:
            # Update the existing instance
            employee_work_info.email = email
            employee_work_info.department_id = department_obj
            employee_work_info.job_position_id = job_position_obj
            employee_work_info.job_role_id = job_role_obj
            employee_work_info.work_type_id = work_type_obj
            employee_work_info.employee_type_id = employee_type_obj
            employee_work_info.shift_id = shift_obj
            employee_work_info.reporting_manager_id = reporting_manager_obj
            employee_work_info.company_id = company_obj
            employee_work_info.location = location
            employee_work_info.date_joining = (
                date_joining if not pd.isnull(date_joining) else datetime.today()
            )
            employee_work_info.contract_end_date = (
                contract_end_date if not pd.isnull(contract_end_date) else None
            )
            employee_work_info.basic_salary = basic_salary
            employee_work_info.salary_hour = salary_hour
            update_work_info_list.append(employee_work_info)

    if new_work_info_list:
        EmployeeWorkInformation.objects.bulk_create(new_work_info_list)
    if update_work_info_list:
        EmployeeWorkInformation.objects.bulk_update(
            update_work_info_list,
            [
                "email",
                "department_id",
                "job_position_id",
                "job_role_id",
                "work_type_id",
                "employee_type_id",
                "shift_id",
                "reporting_manager_id",
                "company_id",
                "location",
                "date_joining",
                "contract_end_date",
                "basic_salary",
                "salary_hour",
            ],
        )
    if apps.is_installed("payroll"):

        contract_creation_thread = threading.Thread(
            target=create_contracts_in_thread,
            args=(new_work_info_list, update_work_info_list),
        )
        contract_creation_thread.start()
