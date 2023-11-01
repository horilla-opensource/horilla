"""
views.py

This module is used to map url pattens with django views or methods
"""
from datetime import date, timedelta, datetime
from urllib.parse import parse_qs
import uuid
import json
from django.db.models import ProtectedError
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.utils.translation import gettext as _
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User, Permission
from attendance.forms import AttendanceValidationConditionForm
from attendance.models import AttendanceValidationCondition
from base.decorators import (
    shift_request_change_permission,
    work_type_request_change_permission,
)
from notifications.signals import notify
from horilla.decorators import permission_required, login_required, manager_can_enter
from horilla.settings import EMAIL_HOST_USER
from employee.models import Employee
from base.forms import (
    CompanyForm,
    DepartmentForm,
    JobPositionForm,
    JobRoleForm,
    EmployeeShiftForm,
    EmployeeShiftScheduleForm,
    EmployeeTypeForm,
    WorkTypeForm,
    UserGroupForm,
    RotatingShiftForm,
    RotatingShiftAssign,
    RotatingWorkTypeForm,
    RotatingWorkTypeAssignForm,
    RotatingShiftAssignForm,
    ShiftRequestForm,
    WorkTypeRequestForm,
    RotatingShiftAssignUpdateForm,
    RotatingWorkTypeAssignUpdateForm,
    EmployeeShiftScheduleUpdateForm,
    AssignUserGroup,
    AssignPermission,
    ResetPasswordForm,
    ChangePasswordForm,
)
from base.models import (
    Company,
    JobPosition,
    JobRole,
    Department,
    WorkType,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeShiftSchedule,
    EmployeeType,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    RotatingShift,
    ShiftRequest,
    WorkTypeRequest,
)
from base.filters import (
    ShiftRequestFilter,
    WorkTypeRequestFilter,
    RotatingShiftAssignFilters,
    RotatingWorkTypeAssignFilter,
)
from base.methods import (
    choosesubordinates,
    filtersubordinates,
    get_key_instances,
    sortby,
)
from payroll.forms.component_forms import PayrollSettingsForm
from payroll.models.tax_models import PayrollSettings


def custom404(request):
    """
    Custom 404 method
    """
    return render(request, "404.html")


# Create your views here.
def is_reportingmanger(request, instance):
    """
    If the instance have employee id field then you can use this method to know the request
    user employee is the reporting manager of the instance
    """
    manager = request.user.employee_get
    try:
        employee_work_info_manager = (
            instance.employee_id.employee_work_info.reporting_manager_id
        )
    except Exception:
        return HttpResponse("This Employee Dont Have any work information")
    return manager == employee_work_info_manager


def paginator_qry(queryset, page_number):
    """
    Common paginator method
    """
    paginator = Paginator(queryset, 50)
    queryset = paginator.get_page(page_number)
    return queryset


def login_user(request):
    """
    This method is used render login template and authenticate user
    """

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, _("Invalid username or password."))
            return redirect("/login")
        login(request, user)
        messages.success(request, _("Login Success"))
        return redirect("/")
    return render(request, "login.html")


def include_employee_instance(request, form):
    """
    This method is used to include the employee instance to the form
    Args:
        form: django forms instance
    """
    queryset = form.fields["employee_id"].queryset
    employee = Employee.objects.filter(employee_user_id=request.user)
    if employee.first() is not None:
        if queryset.filter(id=employee.first().id).first() is None:
            queryset = queryset | employee
            form.fields["employee_id"].queryset = queryset
    return form


reset_ids = []


def forgot_password(request):
    """
    This method is used to send the reset password link to the employee email
    """
    if request.method == "POST":
        id = str(uuid.uuid4())
        username = request.POST["email"]
        user = User.objects.filter(username=username).first()
        if user is not None:
            employee = Employee.objects.filter(employee_user_id=user).first()
            if employee is not None:
                if employee.email is not None:
                    send_link(employee, request, id, user)
                else:
                    messages.error(request, _("No email found."))
        else:
            messages.error(request, "User not found")
    return render(request, "forgot_password.html")


def send_link(employee, request, id, user):
    """
    Here actually the link will send to the employee email
    """
    recipient = [
        employee.email,
    ]
    subject = "Link To Rest Your Password!"
    url = request.build_absolute_uri("/") + "reset-password/" + id
    message = f"Reset Your Password {url}."
    reset_ids.append({"uuid": id, "user": user})
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=EMAIL_HOST_USER,
            recipient_list=recipient,
        )
        response_success = _("Link sended to {recipient}").format(recipient=recipient)
        messages.success(request, response_success)
    except Exception as e:
        messages.error(request, e)


def reset_password(request, uuid):
    """
    This method is used to reset the current password for the employee
    """
    user = next((item["user"] for item in reset_ids if item["uuid"] == uuid), None)
    form = ResetPasswordForm()
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            form.save(user=user)
            messages.success(request, _("Password reset success"))
            reset_ids.remove({"uuid": uuid, "user": user})
            return redirect("/login")
    if user is None:
        return HttpResponse(_("Link Expired..."))
    return render(request, "reset_password.html", {"form": form})


@login_required
def change_password(request):
    user = request.user
    form = ChangePasswordForm(user=user)
    if request.method == "POST":
        response = render(request, "base/auth/password_change.html", {"form": form})
        form = ChangePasswordForm(user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            user.set_password(new_password)
            user.save()
            user = authenticate(request, username=user.username, password=new_password)
            login(request, user)
            messages.success(request, _("Password changed successfully"))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "base/auth/password_change.html", {"form": form})


def logout_user(request):
    """
    This method used to logout the user
    """
    if request.user:
        logout(request)
    response = HttpResponse()
    response.content = """
        <script>
            localStorage.clear();
        </script>
        <meta http-equiv="refresh" content="0;url=/login">
    """

    return response


@login_required
def home(request):
    """
    This method is used to render index page
    """
    if len(EmployeeShiftDay.objects.all()) == 0:
        days = (
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
        )
        for day in days:
            shift_day = EmployeeShiftDay()
            shift_day.day = day[0]
            shift_day.save()

    today = datetime.today()
    today_weekday = today.weekday()
    first_day_of_week = today - timedelta(days=today_weekday)
    last_day_of_week = first_day_of_week + timedelta(days=6)

    context = {
        "first_day_of_week": first_day_of_week.strftime("%Y-%m-%d"),
        "last_day_of_week": last_day_of_week.strftime("%Y-%m-%d"),
    }

    return render(request, "index.html", context)


@login_required
def common_settings(request):
    """
    This method is used to render setting page template
    """
    return render(request, "settings.html")


@login_required
@permission_required("add_group")
def user_group_create(request):
    """
    This method is used to create user permission group
    """

    form = UserGroupForm()
    groups = Group.objects.all()
    if request.method == "POST":
        form = UserGroupForm(request.POST)
        if form.is_valid():
            form.save()
            form = UserGroupForm()

            messages.success(request, _("User group created."))
            return redirect(user_group_create)

    return render(request, "base/auth/group.html", {"form": form, "groups": groups})


@login_required
@permission_required("add_group")
def group_assign(request):
    """
    This method is used to assign user group to the users.
    """
    form = AssignUserGroup()
    groups = Group.objects.all()
    if request.POST:
        form = AssignUserGroup(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("User group assigned."))
            return redirect(group_assign)

    return render(
        request,
        "base/auth/group_assign.html",
        {"form": form, "groups": paginator_qry(groups, request.GET.get("page"))},
    )


@login_required
@permission_required("view_group")
def group_assign_view(request):
    """
    This method is used to search the user groups
    """
    search = ""
    if request.GET.get("search") is not None:
        search = request.GET.get("search")
    groups = Group.objects.filter(name__icontains=search)
    previous_data = request.GET.urlencode()
    return render(
        request,
        "base/auth/group_assign_view.html",
        {"groups": paginator_qry(groups, request.GET.get("page")), "pd": previous_data},
    )


@login_required
@permission_required("base.view_group")
def user_group_view(request):
    """
    This method is used to render template for view all groups
    """
    search = ""
    if request.GET.get("search") is not None:
        search = request.GET["search"]
    user_group = Group.objects.filter()
    return render(request, "base/auth/group_assign.html", {"data": user_group})


@login_required
@permission_required("change_group")
@require_http_methods(["POST"])
def user_group_permission_remove(request, pid, gid):
    """
    This method is used to remove permission from group.
    args:
        pid: permission id
        gid: group id
    """
    group = Group.objects.get(id=1)
    permission = Permission.objects.get(id=2)
    group.permissions.remove(permission)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("change_group")
@require_http_methods(["POST"])
def group_remove_user(request, uid, gid):
    """
    This method is used to remove an user from group permission.
    args:
        uid: user instance id
        gid: group instance id
    """
    group = Group.objects.get(id=gid)
    user = User.objects.get(id=uid)
    group.user_set.remove(user)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("change_group")
def user_group_update(request, id):
    """
    This method is used to render updating form template for user permission group
    args:
        id : group instance id
    """
    group = Group.objects.get(id=id)
    form = UserGroupForm(instance=group)
    if request.method == "POST":
        form = UserGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, _("User group updated."))
            return redirect(user_group_create)

    groups = Group.objects.all()
    return render(request, "base/auth/group.html", {"form": form, "groups": groups})


@login_required
@permission_required("base.delete_group")
@require_http_methods(["POST"])
def user_group_delete(request, id):
    """
    This method is used to delete user group
    args:
        id : group instance id

    """
    try:
        user_group = Group.objects.get(id=id).delete()
        messages.success(request, _("User group deleted."))
    except Group.DoesNotExist:
        messages.error(request, _("User group not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this user group."))
    return redirect("/settings/user-group-create")


@login_required
@permission_required("base.add_company")
def company_create(request):
    """
    This method render template and form to create company and save if the form is valid
    """

    form = CompanyForm()
    companies = Company.objects.all()
    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            form = CompanyForm()

            messages.success(request, _("Company has been created successfully!"))
            return redirect(company_create)

    return render(
        request, "base/company/company.html", {"form": form, "companies": companies}
    )


@login_required
@permission_required("base.change_company")
def company_update(request, id):
    """
    This method is used to update company
    args:
        id : company instance id

    """
    companies = Company.objects.all()
    company = Company.objects.get(id=id)
    form = CompanyForm(instance=company)
    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _("Company updated"))
            return redirect(company_create)
    return render(
        request, "base/company/company.html", {"form": form, "companies": companies}
    )


@login_required
@permission_required("base.base.delete_company")
@require_http_methods(["POST"])
def company_delete(request, id):
    """
    This method is used to delete company
    args:
        id : company instance id

    """

    try:
        company = Company.objects.get(id=id).delete()
        messages.success(request, _("Company deleted."))
    except Company.DoesNotExist:
        messages.error(request, _("Company not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)
        messages.error(
            request, _("This company is already in use for {}.").format(model_names_str)
        )

    return redirect(company_create)


@login_required
@permission_required("base.add_department")
def department(request):
    """
    This method render renders form and template to create department
    """

    form = DepartmentForm()
    departments = Department.objects.all()
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            form = DepartmentForm()
            messages.success(request, _("Department has been created successfully!"))
    return render(
        request,
        "base/department/department.html",
        {"form": form, "departments": departments},
    )


@login_required
@permission_required("base.change_department")
def department_update(request, id):
    """
    This method is used to update department
    args:
        id : department instance id
    """
    department = Department.objects.get(id=id)
    departments = Department.objects.all()
    form = DepartmentForm(instance=department)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, _("Department updated."))
            return redirect("/settings/department-creation")
    return render(
        request,
        "base/department/department.html",
        {"form": form, "departments": departments},
    )


@login_required
@permission_required("base.delete_department")
@require_http_methods(["POST", "DELETE"])
def department_delete(request, id):
    """
    This method is used to delete department instance
    args:
        id : department instance id
    """

    try:
        departments = Department.objects.get(id=id).delete()
        messages.success(request, _("Department deleted."))
    except Department.DoesNotExist:
        messages.error(request, _("Department not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)
        messages.error(
            request,
            _("This department is already in use for {}.").format(model_names_str),
        ),

    return redirect("/settings/department-creation")


@login_required
@permission_required("base.add_jobposition")
def job_position(request):
    """
    This method is used to create job position
    """

    departments = Department.objects.all()
    form = JobPositionForm()
    if request.method == "POST":
        form = JobPositionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Job Position has been created successfully!"))
    return render(
        request,
        "base/job_position/job_position.html",
        {"form": form, "departments": departments},
    )


@login_required
@permission_required("base.change_jobposition")
def job_position_update(request, id):
    """
    This method is used to update job position
    args:
        id : job position instance id

    """
    job_position = JobPosition.objects.get(id=id)
    departments = Department.objects.all()
    form = JobPositionForm(instance=job_position)
    if request.method == "POST":
        form = JobPositionForm(request.POST, instance=job_position)
        if form.is_valid():
            form.save()
            messages.success(request, _("Job position updated."))
            return redirect("/settings/job-position-creation")
    return render(
        request,
        "base/job_position/job_position.html",
        {"form": form, "departments": departments},
    )


@login_required
@permission_required("base.delete_jobposition")
@require_http_methods(["POST"])
def job_position_delete(request, id):
    """
    This method is used to delete job position
    args:
        id : job position id
    """

    try:
        job_position = JobPosition.objects.get(id=id).delete()
        messages.success(request, _("Job Position Deleted."))
    except JobPosition.DoesNotExist:
        messages.error(request, _("JobPosition not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))
        model_names_str = ", ".join(model_verbose_names_set)

        messages.error(
            request,
            _("This job position is already in use for {}.").format(model_names_str),
        ),

    return redirect("/settings/job-position-creation")


@login_required
@permission_required("base.add_jobrole")
def job_role_create(request):
    """
    This method is used to create job role.
    """

    form = JobRoleForm()
    jobs = JobPosition.objects.all()
    if request.method == "POST":
        form = JobRoleForm(request.POST)
        if form.is_valid():
            form.save()
            form = JobRoleForm()

            messages.success(request, _("Job role has been created successfully!"))
    return render(
        request, "base/job_role/job_role.html", {"form": form, "job_positions": jobs}
    )


@login_required
@permission_required("base.change_jobrole")
def job_role_update(request, id):
    """
    This method is used to update job role instance
    args:
        id  : job role instance id

    """

    job_role = JobRole.objects.get(id=id)
    jobs = JobPosition.objects.all()

    form = JobRoleForm(instance=job_role)
    if request.method == "POST":
        form = JobRoleForm(request.POST, instance=job_role)
        if form.is_valid():
            form.save()
            messages.success(request, _("Job role updated."))
    return render(
        request, "base/job_role/job_role.html", {"form": form, "job_positions": jobs}
    )


@login_required
@permission_required("base.delete_jobrole")
@require_http_methods(["POST"])
def job_role_delete(request, id):
    """
    This method is used to delete job role
    args:
        id : job role instance id
    """
    try:
        job_role = JobRole.objects.get(id=id).delete()
        messages.success(request, _("Job Role Deleted."))
    except JobRole.DoesNotExist:
        messages.error(request, _("Job role not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)

        messages.error(
            request,
            _("This job role is already in use for {}.").format(model_names_str),
        ),

    return redirect("/settings/job-role-create")


@login_required
@permission_required("base.add_worktype")
def work_type_create(request):
    """
    This method is used to create work type
    """

    form = WorkTypeForm()
    work_types = WorkType.objects.all()
    if request.method == "POST":
        form = WorkTypeForm(request.POST)
        if form.is_valid():
            form.save()
            form = WorkTypeForm()

            messages.success(request, _("Work Type has been created successfully!"))
    return render(
        request,
        "base/work_type/work_type.html",
        {"form": form, "work_types": work_types},
    )


@login_required
@permission_required("base.change_worktype")
def work_type_update(request, id):
    """
    This method is used to update work type instance
    args:
        id : work type instance id

    """

    work_type = WorkType.objects.get(id=id)
    work_types = WorkType.objects.all()
    form = WorkTypeForm(instance=work_type)
    if request.method == "POST":
        form = WorkTypeForm(request.POST, instance=work_type)
        if form.is_valid():
            form.save()
            messages.success(request, _("Work type updated."))
            return redirect(work_type_create)
    return render(
        request,
        "base/work_type/work_type.html",
        {"form": form, "work_types": work_types},
    )


@login_required
@permission_required("base.delete_worktype")
@require_http_methods(["POST", "DELETE"])
def work_type_delete(request, id):
    """
    This method is used to delete work type instance
    args:
        id : work type instance id
    """
    try:
        work_type = WorkType.objects.get(id=id).delete()
        messages.success(request, _("Work type deleted."))
    except WorkType.DoesNotExist:
        messages.error(request, _("Work type not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)

        messages.error(
            request,
            _("This work type is already in use for {}.").format(model_names_str),
        ),

    return redirect("/settings/work-type-create")


@login_required
@permission_required("base.add_rotatingworktype")
def rotating_work_type_create(request):
    """
    This method is used to create rotating work type   .
    """

    form = RotatingWorkTypeForm()
    if request.method == "POST":
        form = RotatingWorkTypeForm(request.POST)
        if form.is_valid():
            form.save()
            form = RotatingWorkTypeForm()

            messages.success(request, _("Rotating work type created."))
            return redirect(rotating_work_type_create)
    return render(
        request,
        "base/rotating_work_type/rotating_work_type.html",
        {"form": form, "rwork_type": RotatingWorkType.objects.all()},
    )


@login_required
@permission_required("base.change_rotatingworktype")
def rotating_work_type_update(request, id):
    """
    This method is used to update rotating work type instance.
    args:
        id : rotating work type instance id

    """

    rotating_work_type = RotatingWorkType.objects.get(id=id)
    form = RotatingWorkTypeForm(instance=rotating_work_type)
    if request.method == "POST":
        form = RotatingWorkTypeForm(request.POST, instance=rotating_work_type)
        if form.is_valid():
            form.save()
            messages.success(request, _("Rotating work type updated."))
            return redirect(rotating_work_type_create)
    return render(
        request,
        "base/rotating_work_type/rotating_work_type.html",
        {"form": form, "rwork_type": RotatingWorkType.objects.all()},
    )


@login_required
@permission_required("base.delete_rotatingworktype")
@require_http_methods(["POST", "DELETE"])
def rotating_work_type_delete(request, id):
    """
    This method is used to delete rotating work type
    args:
        id : rotating work type id

    """
    try:
        rotating_work_type = RotatingWorkType.objects.get(id=id).delete()
        messages.success(request, _("Rotating work type deleted."))
    except RotatingWorkType.DoesNotExist:
        messages.error(request, _("Rotating work type not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)

        messages.error(
            request,
            _("This rotating work type is already in use for {}.").format(
                model_names_str
            ),
        ),

    return redirect("/settings/rotating-work-type-create")


@login_required
@manager_can_enter("base.view_rotatingworktypeassign")
def rotating_work_type_assign(request):
    """
    This method is used to assign rotating work type to employee users
    """

    filter = RotatingWorkTypeAssignFilter(
        queryset=RotatingWorkTypeAssign.objects.filter(is_active=True)
    )
    rwork_type_assign = filter.qs
    rwork_type_assign = filtersubordinates(
        request, rwork_type_assign, "base.view_rotatingworktypeassign"
    )

    return render(
        request,
        "base/rotating_work_type/rotating_work_type_assign.html",
        {
            "f": filter,
            "rwork_type_assign": paginator_qry(
                rwork_type_assign, request.GET.get("page")
            ),
        },
    )


@login_required
@manager_can_enter("base.add_rotatingworktypeassign")
def rotating_work_type_assign_add(request):
    """
    This method is used to assign rotating work type
    """
    form = RotatingWorkTypeAssignForm()
    if request.GET.get("emp_id"):
        employee = request.GET.get("emp_id")
        form = RotatingWorkTypeAssignForm(initial={"employee_id": employee})
    form = choosesubordinates(request, form, "base.add_rotatingworktypeassign")
    if request.method == "POST":
        form = RotatingWorkTypeAssignForm(request.POST)
        form = choosesubordinates(request, form, "base.add_rotatingworktypeassign")
        if form.is_valid():
            form.save()
            employee_ids = request.POST.getlist("employee_id")
            employees = Employee.objects.filter(id__in=employee_ids).select_related(
                "employee_user_id"
            )
            users = [employee.employee_user_id for employee in employees]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are added to rotating work type",
                verb_ar="تمت إضافتك إلى نوع العمل المتناوب",
                verb_de="Sie werden zum rotierenden Arbeitstyp hinzugefügt",
                verb_es="Se le agrega al tipo de trabajo rotativo",
                verb_fr="Vous êtes ajouté au type de travail rotatif",
                icon="infinite",
                redirect="/employee/rotating-work-type-assign",
            )

            messages.success(request, _("Rotating work type assigned."))
            response = render(
                request,
                "base/rotating_work_type/htmx/rotating_work_type_assign_form.html",
                {"form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "base/rotating_work_type/htmx/rotating_work_type_assign_form.html",
        {"form": form},
    )


@login_required
@manager_can_enter("base.view_rotatingworktypeassign")
def rotating_work_type_assign_view(request):
    """
    This method renders template to view rotating work type objects
    """

    previous_data = request.GET.urlencode()
    rwork_type_assign = RotatingWorkTypeAssignFilter(request.GET).qs
    if request.GET.get("is_active") is None:
        rwork_type_assign = rwork_type_assign.filter(is_active=True)
    rwork_type_assign = filtersubordinates(
        request, rwork_type_assign, "base.view_rotatingworktypeassign"
    )
    rwork_type_assign = sortby(request, rwork_type_assign, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(RotatingWorkTypeAssign, data_dict)
    return render(
        request,
        "base/rotating_work_type/rotating_work_type_assign_view.html",
        {
            "rwork_type_assign": paginator_qry(
                rwork_type_assign, request.GET.get("page")
            ),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@manager_can_enter("base.change_rotatingworktypeassign")
def rotating_work_type_assign_update(request, id):
    """
    This method is used to update rotating work type instance
    """

    rotating_work_type_assign_obj = RotatingWorkTypeAssign.objects.get(id=id)
    form = RotatingWorkTypeAssignUpdateForm(instance=rotating_work_type_assign_obj)
    form = choosesubordinates(request, form, "base.change_rotatingworktypeassign")
    if request.method == "POST":
        form = RotatingWorkTypeAssignUpdateForm(
            request.POST, instance=rotating_work_type_assign_obj
        )
        form = choosesubordinates(request, form, "base.change_rotatingworktypeassign")
        if form.is_valid():
            form.save()
            messages.success(request, _("Rotating work type assign updated."))
            response = render(
                request,
                "base/rotating_work_type/htmx/rotating_work_type_assign_update_form.html",
                {"update_form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "base/rotating_work_type/htmx/rotating_work_type_assign_update_form.html",
        {"update_form": form},
    )


@login_required
@manager_can_enter("base.change_rotatingworktypeassign")
def rotating_work_type_assign_archive(request, id):
    """
    This method is used to archive or un-archive rotating work type assigns
    """
    rwork_type = RotatingWorkTypeAssign.objects.get(id=id)
    employees_rwork_types = RotatingWorkTypeAssign.objects.filter(
        is_active=True, employee_id=rwork_type.employee_id
    )
    flag = False
    if len(employees_rwork_types) < 1:
        rwork_type.is_active = True
        flag = True

    message = _("un-archived")
    if request.GET.get("is_active") == "False":
        rwork_type.is_active = False
        message = _("archived")
        flag = True
    rwork_type.save()
    if flag:
        messages.success(
            request, _("Rotating shift assign is {message}").format(message=message)
        )
    else:
        messages.error(request, "Already on record is active")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@manager_can_enter("base.change_rotatingworktypeassign")
def rotating_work_type_assign_bulk_archive(request):
    """
    This method is used to archive/un-archive bulk rotating work type assigns
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = True
    message = _("un-archived")
    if request.GET.get("is_active") == "False":
        is_active = False
        message = _("archived")
    for id in ids:
        # check permission right here...
        rwork_type_assign = RotatingWorkTypeAssign.objects.get(id=id)
        employees_rwork_type_assign = RotatingWorkTypeAssign.objects.filter(
            is_active=True, employee_id=rwork_type_assign.employee_id
        )
        flag = True
        if is_active:
            if len(employees_rwork_type_assign) < 1:
                flag = False
                rwork_type_assign.is_active = is_active
        else:
            flag = False
            rwork_type_assign.is_active = is_active
        rwork_type_assign.save()
        if not flag:
            messages.success(
                request,
                _("Rotating work type for {employee_id} is {message}").format(
                    employee_id=rwork_type_assign.employee_id, message=message
                ),
            )
        else:
            messages.error(
                request,
                _("Rotating work type for {employee_id} is already exists").format(
                    employee_id=rwork_type_assign.employee_id,
                ),
            )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("base.delete_rotatingworktypeassign")
def rotating_work_type_assign_bulk_delete(request):
    """
    This method is used to archive/un-archive bulk rotating work type assigns
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for id in ids:
        try:
            rwork_type_assign = RotatingWorkTypeAssign.objects.get(id=id)
            rwork_type_assign.delete()
            messages.success(
                request,
                _("{employee} deleted.").format(employee=rwork_type_assign.employee_id),
            )
        except RotatingWorkTypeAssign.DoesNotExist:
            messages.error(request, _("{rwork_type_assign} not found."))
        except ProtectedError:
            messages.error(
                request,
                _("You cannot delete {rwork_type_assign}").format(
                    rwork_type_assign=rwork_type_assign
                ),
            )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("base.delete_rotatingworktypeassign")
@require_http_methods(["POST"])
def rotating_work_type_assign_delete(request, id):
    """
    This method is used to delete rotating work type
    """
    try:
        rotating_work_type_assign_obj = RotatingWorkTypeAssign.objects.get(
            id=id
        ).delete()
        messages.success(request, _("Rotating work type assign deleted."))
    except RotatingWorkTypeAssign.DoesNotExist:
        messages.error(request, _("Rotating work type assign not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this rotating work type."))

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("base.add_employeetype")
def employee_type_create(request):
    """
    This method is used to create employee type
    """

    form = EmployeeTypeForm()
    types = EmployeeType.objects.all()
    if request.method == "POST":
        form = EmployeeTypeForm(request.POST)
        if form.is_valid():
            form.save()
            form = EmployeeTypeForm()
            messages.success(request, _("Employee type created."))
    return render(
        request,
        "base/employee_type/employee_type.html",
        {"form": form, "employee_types": types},
    )


@login_required
@permission_required("base.change_employeetype")
def employee_type_update(request, id):
    """
    This method is used to update employee type instance
    args:
        id : employee type instance id

    """

    employee_type = EmployeeType.objects.get(id=id)
    employee_types = EmployeeType.objects.all()
    form = EmployeeTypeForm(instance=employee_type)
    if request.method == "POST":
        form = EmployeeTypeForm(request.POST, instance=employee_type)
        if form.is_valid():
            form.save()
            messages.success(request, _("Employee type updated."))
            return redirect(employee_type_create)
    return render(
        request,
        "base/employee_type/employee_type.html",
        {"form": form, "employee_types": employee_types},
    )


@login_required
@permission_required("base.delete_employeetype")
@require_http_methods(["POST"])
def employee_type_delete(request, id):
    """
    This method is used to delete employee type
    args:
        id : employee type id
    """
    try:
        employee_type = EmployeeType.objects.get(id=id).delete()
        messages.success(request, _("Employee type deleted."))
    except EmployeeType.DoesNotExist:
        messages.error(request, _("Employee type not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)

        messages.error(
            request,
            _("This employee type is already in use for {}.").format(model_names_str),
        ),

    return redirect("/settings/employee-type-create")


@login_required
@permission_required("base.add_employeeshift")
def employee_shift_create(request):
    """
    This method is used to create employee shift
    """

    form = EmployeeShiftForm()
    shifts = EmployeeShift.objects.all()
    if request.method == "POST":
        form = EmployeeShiftForm(request.POST)
        if form.is_valid():
            form.save()
            form = EmployeeShiftForm()
            messages.success(
                request, _("Employee Shift has been created successfully!")
            )
    return render(request, "base/shift/shift.html", {"form": form, "shifts": shifts})


@login_required
@permission_required("base.change_employeeshiftupdate")
def employee_shift_update(request, id):
    """
    This method is used to update employee shift instance
    args:
        id  : employee shift id

    """
    employee_shift = EmployeeShift.objects.get(id=id)
    employee_shifts = EmployeeShift.objects.all()
    form = EmployeeShiftForm(instance=employee_shift)
    if request.method == "POST":
        form = EmployeeShiftForm(request.POST, instance=employee_shift)
        if form.is_valid():
            form.save()
            messages.success(request, _("Shift updated"))
            return redirect(employee_shift_create)
    return render(
        request, "base/shift/shift.html", {"form": form, "shifts": employee_shifts}
    )


@login_required
@permission_required("base.delete_employeeshift")
@require_http_methods(["POST"])
def employee_shift_delete(request, id):
    """
    This method is used to delete shift
    args:
        id : employee shift instance id
    """

    try:
        employee_shift = EmployeeShift.objects.get(id=id).delete()
        messages.success(request, _("Employee shift deleted."))
    except EmployeeShift.DoesNotExist:
        messages.error(request, _("This shift not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)
        messages.error(
            request, _("This shift is already in use for {}.").format(model_names_str)
        )

    return redirect("/settings/employee-shift-create")


@login_required
@permission_required("base.add_employeeshiftschedule")
def employee_shift_schedule_create(request):
    """
    This method is used to create schedule for shift
    """

    form = EmployeeShiftScheduleForm()
    shifts = EmployeeShift.objects.all()
    if request.method == "POST":
        form = EmployeeShiftScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            form = EmployeeShiftScheduleForm()
            messages.success(
                request, _("Employee Shift Schedule has been created successfully!")
            )
    return render(request, "base/shift/schedule.html", {"form": form, "shifts": shifts})


@login_required
@permission_required("base.change_employeeshiftschedule")
def employee_shift_schedule_update(request, id):
    """
    This method is used to update employee shift instance
    args:
        id : employee shift instance id
    """

    employee_shift_schedule = EmployeeShiftSchedule.objects.get(id=id)
    form = EmployeeShiftScheduleUpdateForm(instance=employee_shift_schedule)
    shifts = EmployeeShift.objects.all()
    if request.method == "POST":
        form = EmployeeShiftScheduleUpdateForm(
            request.POST, instance=employee_shift_schedule
        )
        if form.is_valid():
            form.save()
            messages.success(request, _("Shift schedule created."))
            return redirect(employee_shift_schedule_create)
    return render(request, "base/shift/schedule.html", {"form": form, "shifts": shifts})


@login_required
@permission_required("base.delete_employeeshiftschedule")
@require_http_methods(["POST"])
def employee_shift_schedule_delete(request, id):
    """
    This method is used to delete employee shift instance
    args:
        id : employee shift instance id
    """
    try:
        employee_shift_schedule = EmployeeShiftSchedule.objects.get(id=id).delete()
        messages.success(request, _("Shift schedule deleted."))
    except EmployeeShiftSchedule.DoesNotExist:
        messages.error(request, _("Shift schedule not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this schedule"))
    return redirect("/settings/employee-shift-schedule-create")


@login_required
@permission_required("base.add_rotatingshift")
def rotating_shift_create(request):
    """
    This method is used to create rotating shift
    """

    form = RotatingShiftForm()
    if request.method == "POST":
        form = RotatingShiftForm(request.POST)
        if form.is_valid():
            form.save()
            form = RotatingShiftForm()
            messages.success(request, _("Rotating shift created."))
    return render(
        request,
        "base/rotating_shift/rotating_shift.html",
        {"form": form, "rshifts": RotatingShift.objects.all()},
    )


@login_required
@permission_required("base.change_rotatingshift")
def rotating_shift_update(request, id):
    """
    This method is used to update rotating shift instance
    args:
        id : rotating shift instance id
    """

    rotating_shift = RotatingShift.objects.get(id=id)
    form = RotatingShiftForm(instance=rotating_shift)
    if request.method == "POST":
        form = RotatingShiftForm(request.POST, instance=rotating_shift)
        if form.is_valid():
            form.save()
            form = RotatingShiftForm()
            messages.success(request, _("Rotating shift updated."))
            return redirect(rotating_shift_create)
    return render(
        request,
        "base/rotating_shift/rotating_shift.html",
        {
            "form": form,
            "rshifts": paginator_qry(
                RotatingShift.objects.all(), request.GET.get("page")
            ),
        },
    )


@login_required
@permission_required("base.delete_rotatingshift")
@require_http_methods(["POST"])
def rotating_shift_delete(request, id):
    """
    This method is used to delete rotating shift
    args:
        id : rotating shift instance id

    """
    try:
        rotating_shift = RotatingShift.objects.get(id=id).delete()
        messages.success(request, _("Rotating shift deleted."))
    except RotatingShift.DoesNotExist:
        messages.error(request, _("Rotating shift not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(_(obj._meta.verbose_name.capitalize()))

        model_names_str = ", ".join(model_verbose_names_set)
        messages.error(
            request,
            _("This rotating shift is already in use for {}.").format(model_names_str),
        ),

    return redirect(rotating_shift_create)


@login_required
@manager_can_enter("base.view_rotatingshiftassign")
def rotating_shift_assign(request):
    """
    This method is used to assign rotating shift
    """

    form = RotatingShiftAssignForm()
    form = choosesubordinates(request, form, "base.add_rotatingshiftassign")
    filter = RotatingShiftAssignFilters(
        queryset=RotatingShiftAssign.objects.filter(is_active=True)
    )
    rshift_assign = filter.qs
    rshift_assign = filtersubordinates(
        request, rshift_assign, "base.view_rotatingshiftassign"
    )

    return render(
        request,
        "base/rotating_shift/rotating_shift_assign.html",
        {
            "form": form,
            "f": filter,
            "rshift_assign": paginator_qry(rshift_assign, request.GET.get("page")),
        },
    )


@login_required
@manager_can_enter("base.add_rotatingshiftassign")
def rotating_shift_assign_add(request):
    """
    This method is used to add rotating shift assign
    """
    form = RotatingShiftAssignForm()
    if request.GET.get("emp_id"):
        employee = request.GET.get("emp_id")
        form = RotatingShiftAssignForm(initial={"employee_id": employee})
    form = choosesubordinates(request, form, "base.add_rotatingshiftassign")
    if request.method == "POST":
        form = RotatingShiftAssignForm(request.POST)
        form = choosesubordinates(request, form, "base.add_rotatingshiftassign")
        if form.is_valid():
            form.save()
            employee_ids = request.POST.getlist("employee_id")
            employees = Employee.objects.filter(id__in=employee_ids).select_related(
                "employee_user_id"
            )
            users = [employee.employee_user_id for employee in employees]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are added to rotating shift",
                verb_ar="تمت إضافتك إلى وردية الدورية",
                verb_de="Sie werden der rotierenden Arbeitsschicht hinzugefügt",
                verb_es="Estás agregado a turno rotativo",
                verb_fr="Vous êtes ajouté au quart de travail rotatif",
                icon="infinite",
                redirect="/employee/rotating-shift-assign",
            )

            messages.success(request, _("Rotating shift assigned."))
            response = render(
                request,
                "base/rotating_shift/htmx/rotating_shift_assign_form.html",
                {"form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "base/rotating_shift/htmx/rotating_shift_assign_form.html",
        {"form": form},
    )


@login_required
@manager_can_enter("base.view_rotatingshiftassign")
def rotating_shift_assign_view(request):
    """
    This method renders all instance of rotating shift assign to a template
    """
    previous_data = request.GET.urlencode()
    rshift_assign = RotatingShiftAssignFilters(request.GET).qs
    if request.GET.get("is_active") is None:
        rshift_assign = rshift_assign.filter(is_active=True)
    rshift_assign = filtersubordinates(
        request, rshift_assign, "base.view_rotatingshiftassign"
    )
    rshift_assign = sortby(request, rshift_assign, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(RotatingShiftAssign, data_dict)
    return render(
        request,
        "base/rotating_shift/rotating_shift_assign_view.html",
        {
            "rshift_assign": paginator_qry(rshift_assign, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@manager_can_enter("base.change_rotatingshiftassign")
def rotating_shift_assign_update(request, id):
    """
    This method is used to update rotating shift assign instance
    args:
        id : rotating shift assign instance id

    """
    rotating_shift_assign_obj = RotatingShiftAssign.objects.get(id=id)
    form = RotatingShiftAssignUpdateForm(instance=rotating_shift_assign_obj)
    form = choosesubordinates(request, form, "base.change_rotatingshiftassign")
    if request.method == "POST":
        form = RotatingShiftAssignUpdateForm(
            request.POST, instance=rotating_shift_assign_obj
        )
        form = choosesubordinates(request, form, "base.change_rotatingshiftassign")
        if form.is_valid():
            form.save()
            messages.success(request, _("Rotating shift assign updated."))
            response = render(
                request,
                "base/rotating_shift/htmx/rotating_shift_assign_update_form.html",
                {
                    "update_form": form,
                },
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "base/rotating_shift/htmx/rotating_shift_assign_update_form.html",
        {
            "update_form": form,
        },
    )


@login_required
@manager_can_enter("base.change_rotatingshiftassign")
def rotating_shift_assign_archive(request, id):
    """
    This method is used to archive and unarchive rotating shift assign records
    """
    rshift = RotatingShiftAssign.objects.get(id=id)
    employees_rshift_assign = RotatingShiftAssign.objects.filter(
        is_active=True, employee_id=rshift.employee_id
    )
    flag = False
    if len(employees_rshift_assign) < 1:
        rshift.is_active = True
        flag = True
    message = _("un-archived")
    if request.GET.get("is_active") == "False":
        rshift.is_active = False
        flag = True
        message = _("archived")
    rshift.save()
    if flag:
        messages.success(
            request, _("Rotating shift assign is {message}").format(message=message)
        )
    else:
        messages.error(request, "Already on record is active")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@manager_can_enter("base.change_rotatingshiftassign")
def rotating_shift_assign_bulk_archive(request):
    """
    This method is used to archive/un-archive bulk rotating shift assigns
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = True
    message = _("un-archived")
    if request.GET.get("is_active") == "False":
        is_active = False
        message = _("archived")
    for id in ids:
        # check permission right here...
        rshift_assign = RotatingShiftAssign.objects.get(id=id)
        employees_rshift_assign = RotatingShiftAssign.objects.filter(
            is_active=True, employee_id=rshift_assign.employee_id
        )
        flag = True
        if is_active:
            if len(employees_rshift_assign) < 1:
                flag = False
                rshift_assign.is_active = is_active
        else:
            flag = False
            rshift_assign.is_active = is_active
        rshift_assign.save()
        if not flag:
            messages.success(
                request,
                _("Rotating shift for {employee} is {message}").format(
                    employee=rshift_assign.employee_id, message=message
                ),
            )
        else:
            messages.error(
                request,
                _("Rotating shift for {employee} is already exists").format(
                    employee=rshift_assign.employee_id
                ),
            )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("base.delete_rotatingshiftassign")
def rotating_shift_assign_bulk_delete(request):
    """
    This method is used to bulk delete for rotating shift assign
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for id in ids:
        try:
            rshift_assign = RotatingShiftAssign.objects.get(id=id)
            rshift_assign.delete()
            messages.success(
                request,
                _("{employee} assign deleted.").format(
                    employee=rshift_assign.employee_id
                ),
            )
        except RotatingShiftAssign.DoesNotExist:
            messages.error(request, _("{rshift_assign} not found."))
        except ProtectedError:
            messages.error(
                request,
                _("You cannot delete {rshift_assign}").format(
                    rshift_assign=rshift_assign
                ),
            )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("base.delete_rotatingshiftassign")
@require_http_methods(["POST"])
def rotating_shift_assign_delete(request, id):
    """
    This method is used to delete rotating shift assign instance
    args:
        id : rotating shift assign instance id
    """
    try:
        rotating_shift_assign_obj = RotatingShiftAssign.objects.get(id=id).delete()
        messages.success(request, _("Rotating shift assign deleted."))
    except RotatingShiftAssign.DoesNotExist:
        messages.error(request, _("Rotating shift assign not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this rotating shift assign."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("add_permission")
def employee_permission_assign(request):
    """
    This method is used to assign permissions to employee user
    """

    employees = Employee.objects.all()
    permissions = Permission.objects.all()
    form = AssignPermission()
    if request.method == "POST":
        form = AssignPermission(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Employee permission assigned."))
            return redirect(employee_permission_assign)

    return render(
        request,
        "base/auth/permission.html",
        {"employees": paginator_qry(employees, request.GET.get("page")), "form": form},
    )


@login_required
@permission_required("view_permissions")
def employee_permission_search(request, codename=None, uid=None):
    """
    This method renders template to view all instances of user permissions
    """

    search = ""
    if request.GET.get("search") is not None:
        search = request.GET.get("search")
    employees = Employee.objects.filter(
        employee_first_name__icontains=search
    ) | Employee.objects.filter(employee_last_name__icontains=search)
    previous_data = request.GET.urlencode()
    return render(
        request,
        "base/auth/permission_view.html",
        {
            "employees": paginator_qry(employees, request.GET.get("page")),
            "pd": previous_data,
        },
    )


@login_required
@require_http_methods(["POST"])
def remove_permission(request, codename, uid):
    """
    This method is used to remove user permission.
    """
    user = User.objects.get(id=uid)
    permission_codename = codename.split(".")[1]
    permission = Permission.objects.filter(codename=permission_codename)
    user.user_permissions.remove(*permission)
    employees = Employee.objects.all()
    page = request.GET.get("page")
    return render(
        request,
        "base/auth/permission_view.html",
        {"employees": paginator_qry(employees, page), "pd": f"&page={page}"},
    )


@login_required
def work_type_request_view(request):
    """
    This method renders template to  view all work type requests
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    work_type_requests = filtersubordinates(
        request, WorkTypeRequest.objects.all(), "base.add_worktyperequest"
    )
    work_type_requests = work_type_requests | WorkTypeRequest.objects.filter(
        employee_id=employee
    )
    f = WorkTypeRequestFilter()
    form = WorkTypeRequestForm()
    form = choosesubordinates(
        request,
        form,
        "base.add_worktypereqeust",
    )
    form = include_employee_instance(request, form)
    return render(
        request,
        "work_type_request/work_type_request_view.html",
        {
            "data": paginator_qry(work_type_requests, request.GET.get("page")),
            "f": f,
            "form": form,
        },
    )


@login_required
def work_type_request_search(request):
    """
    This method is used to search work type request.
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    previous_data = request.GET.urlencode()
    f = WorkTypeRequestFilter(request.GET)
    work_typ_requests = filtersubordinates(request, f.qs, "base.add_worktyperequest")
    if set(WorkTypeRequest.objects.filter(employee_id=employee)).issubset(set(f.qs)):
        work_typ_requests = work_typ_requests | WorkTypeRequest.objects.filter(
            employee_id=employee
        )
    work_typ_requests = sortby(request, work_typ_requests, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(WorkTypeRequest, data_dict)
    return render(
        request,
        "work_type_request/htmx/requests.html",
        {
            "data": paginator_qry(work_typ_requests, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
def work_type_request(request):
    """
    This method is used to create request for work type  .
    """
    form = WorkTypeRequestForm()
    "canceled"
    if request.GET.get("emp_id"):
        employee = request.GET.get("emp_id")
        form = WorkTypeRequestForm(initial={"employee_id": employee})
    form = choosesubordinates(
        request,
        form,
        "base.add_worktyperequest",
    )
    form = include_employee_instance(request, form)

    f = WorkTypeRequestFilter()
    if request.method == "POST":
        form = WorkTypeRequestForm(request.POST)
        form = choosesubordinates(
            request,
            form,
            "base.add_worktyperequest",
        )
        form = include_employee_instance(request, form)
        response = render(
            request, "work_type_request/request_form.html", {"form": form, "f": f}
        )
        if form.is_valid():
            instance = form.save()
            try:
                notify.send(
                    instance.employee_id,
                    recipient=(
                        instance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                    ),
                    verb=f"You have new work type request to \
                            validate for {instance.employee_id}",
                    verb_ar=f"لديك طلب نوع وظيفة جديد للتحقق من \
                            {instance.employee_id}",
                    verb_de=f"Sie haben eine neue Arbeitstypanfrage zur \
                            Validierung für {instance.employee_id}",
                    verb_es=f"Tiene una nueva solicitud de tipo de trabajo para \
                            validar para {instance.employee_id}",
                    verb_fr=f"Vous avez une nouvelle demande de type de travail\
                            à valider pour {instance.employee_id}",
                    icon="information",
                    redirect="/shift-requests/shift-request-view",
                )
            except Exception as error:
                pass
            messages.success(request, _("Work type request added."))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )

    return render(
        request, "work_type_request/request_form.html", {"form": form, "f": f}
    )


@login_required
def work_type_request_cancel(request, id):
    """
    This method is used to cancel work type request
    args:
        id  : work type request id

    """
    work_type_request = WorkTypeRequest.objects.get(id=id)
    if (
        is_reportingmanger(request, work_type_request)
        or request.user.has_perm("base.cancel_worktyperequest")
        or work_type_request.employee_id == request.user.employee_get
        and work_type_request.approved == False
    ):
        work_type_request.canceled = True
        work_type_request.approved = False
        work_type_request.employee_id.employee_work_info.work_type_id = (
            work_type_request.previous_work_type_id
        )
        work_type_request.employee_id.employee_work_info.save()
        work_type_request.save()
        messages.success(request, _("Work type request has been canceled."))
        notify.send(
            request.user.employee_get,
            recipient=work_type_request.employee_id.employee_user_id,
            verb="Your work type request has been canceled.",
            verb_ar="تم إلغاء طلب نوع وظيفتك",
            verb_de="Ihre Arbeitstypanfrage wurde storniert",
            verb_es="Su solicitud de tipo de trabajo ha sido cancelada",
            verb_fr="Votre demande de type de travail a été annulée",
            redirect="/",
            icon="close",
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You dont have permission")


@login_required
@manager_can_enter("base.change_worktyperequest")
def work_type_request_bulk_cancel(request):
    """
    This method is used to cancel a bunch work type request
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    result = False
    for id in ids:
        work_type_request = WorkTypeRequest.objects.get(id=id)
        if (
            is_reportingmanger(request, work_type_request)
            or request.user.has_perm("base.cancel_worktyperequest")
            or work_type_request.employee_id == request.user.employee_get
            and work_type_request.approved == False
        ):
            work_type_request.canceled = True
            work_type_request.approved = False
            work_type_request.employee_id.employee_work_info.work_type_id = (
                work_type_request.previous_work_type_id
            )
            work_type_request.employee_id.employee_work_info.save()
            work_type_request.save()
            messages.success(request, _("Work type request has been canceled."))
            notify.send(
                request.user.employee_get,
                recipient=work_type_request.employee_id.employee_user_id,
                verb="Your work type request has been canceled.",
                verb_ar="تم إلغاء طلب نوع وظيفتك.",
                verb_de="Ihre Arbeitstypanfrage wurde storniert.",
                verb_es="Su solicitud de tipo de trabajo ha sido cancelada.",
                verb_fr="Votre demande de type de travail a été annulée.",
                redirect="/",
                icon="close",
            )
            result = True
    return JsonResponse({"result": result})


@login_required
def work_type_request_approve(request, id):
    """
    This method is used to approve requested work type
    """

    work_type_request = WorkTypeRequest.objects.get(id=id)
    if (
        is_reportingmanger(request, work_type_request)
        or request.user.has_perm("approve_worktyperequest")
        or request.user.has_perm("change_worktyperequest")
        and not work_type_request.approved
    ):
        """
        Here the request will be approved, can send mail right here
        """
        if not work_type_request.is_any_work_type_request_exists():
            work_type_request.approved = True
            work_type_request.canceled = False
            work_type_request.save()
            messages.success(request, _("Work type request has been approved."))
            notify.send(
                request.user.employee_get,
                recipient=work_type_request.employee_id.employee_user_id,
                verb="Your work type request has been approved.",
                verb_ar="تمت الموافقة على طلب نوع وظيفتك.",
                verb_de="Ihre Arbeitstypanfrage wurde genehmigt.",
                verb_es="Su solicitud de tipo de trabajo ha sido aprobada.",
                verb_fr="Votre demande de type de travail a été approuvée.",
                redirect="/",
                icon="checkmark",
            )

            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

        else:
            messages.error(
                request, _("A shift request already exists during this time period.")
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You Do nt Have Permission")


@login_required
def work_type_request_bulk_approve(request):
    """
    This method is used to approve bulk of requested work type
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    result = False
    for id in ids:
        work_type_request = WorkTypeRequest.objects.get(id=id)
        if (
            is_reportingmanger(request, work_type_request)
            or request.user.has_perm("approve_worktyperequest")
            or request.user.has_perm("change_worktyperequest")
            and not work_type_request.approved
        ):
            # """
            # Here the request will be approved, can send mail right here
            # """
            work_type_request.approved = True
            work_type_request.canceled = False
            employee_work_info = work_type_request.employee_id.employee_work_info
            employee_work_info.work_type_id = work_type_request.work_type_id
            employee_work_info.save()
            work_type_request.save()
            messages.success(request, _("Work type request has been approved."))
            notify.send(
                request.user.employee_get,
                recipient=work_type_request.employee_id.employee_user_id,
                verb="Your work type request has been approved.",
                verb_ar="تمت الموافقة على طلب نوع وظيفتك.",
                verb_de="Ihre Arbeitstypanfrage wurde genehmigt.",
                verb_es="Su solicitud de tipo de trabajo ha sido aprobada.",
                verb_fr="Votre demande de type de travail a été approuvée.",
                redirect="/",
                icon="checkmark",
            )
            result = True
    return JsonResponse({"result": result})


@login_required
@work_type_request_change_permission()
def work_type_request_update(request, work_type_request_id):
    """
    This method is used to update work type request instance
    args:
        id : work type request instance id

    """
    work_type_request = WorkTypeRequest.objects.get(id=work_type_request_id)
    form = WorkTypeRequestForm(instance=work_type_request)
    form = choosesubordinates(request, form, "base.change_worktyperequest")
    form = include_employee_instance(request, form)
    if request.method == "POST":
        response = render(
            request,
            "work_type_request/request_update_form.html",
            {
                "form": form,
            },
        )
        form = WorkTypeRequestForm(request.POST, instance=work_type_request)
        form = choosesubordinates(request, form, "base.change_worktyperequest")
        form = include_employee_instance(request, form)
        if form.is_valid():
            form.save()
            messages.success(request, _("Request Updated Successfully"))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )

    return render(request, "work_type_request/request_update_form.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def work_type_request_delete(request, id):
    """
    This method is used to delete work type request
    args:
        id : work type request instance id

    """
    try:
        work_type_request = WorkTypeRequest.objects.get(id=id)
        employee = work_type_request.employee_id.employee_user_id
        work_type_request.delete()
        messages.success(request, _("Work type request deleted."))
        notify.send(
            request.user.employee_get,
            recipient=employee,
            verb="Your work type request has been deleted.",
            verb_ar="تم حذف طلب نوع وظيفتك.",
            verb_de="Ihre Arbeitstypanfrage wurde gelöscht.",
            verb_es="Su solicitud de tipo de trabajo ha sido eliminada.",
            verb_fr="Votre demande de type de travail a été supprimée.",
            redirect="/",
            icon="trash",
        )
    except WorkTypeRequest.DoesNotExist:
        messages.error(request, _("Work type request not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this work type request."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def work_type_request_single_view(request, work_type_request_id):
    try:
        work_type_request = WorkTypeRequest.objects.get(id=work_type_request_id)
    except WorkTypeRequest.DoesNotExist:
        messages.error(request, _("Work type request not found."))
    return render(
        request,
        "work_type_request/htmx/work_type_request_single_view.html",
        context={"work_type_request": work_type_request},
    )


@login_required
@permission_required("base.delete_worktyperequest")
@require_http_methods(["POST"])
def work_type_request_bulk_delete(request):
    """
    This method is used to delete work type request
    args:
        id : work type request instance id

    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for id in ids:
        try:
            work_type_request = WorkTypeRequest.objects.get(id=id)
            user = work_type_request.employee_id.employee_user_id
            work_type_request.delete()
            messages.success(request, _("Work type request deleted."))
            notify.send(
                request.user.employee_get,
                recipient=user,
                verb="Your work type request has been deleted.",
                verb_ar="تم حذف طلب نوع وظيفتك.",
                verb_de="Ihre Arbeitstypanfrage wurde gelöscht.",
                verb_es="Su solicitud de tipo de trabajo ha sido eliminada.",
                verb_fr="Votre demande de type de travail a été supprimée.",
                redirect="/",
                icon="trash",
            )
        except WorkTypeRequest.DoesNotExist:
            messages.error(request, _("Work type request not found."))
        except ProtectedError:
            messages.error(
                request,
                _(
                    "You cannot delete {employee} work type request for the date {date}."
                ).format(
                    employee=work_type_request.employee_id,
                    date=work_type_request.requested_date,
                ),
            )
        result = True
    return JsonResponse({"result": result})


@login_required
def shift_request(request):
    """
    This method is used to create shift request
    """
    form = ShiftRequestForm()
    if request.GET.get("emp_id"):
        employee = request.GET.get("emp_id")
        form = ShiftRequestForm(initial={"employee_id": employee})
    form = choosesubordinates(
        request,
        form,
        "base.add_shiftrequest",
    )
    form = include_employee_instance(request, form)
    f = ShiftRequestFilter()
    if request.method == "POST":
        form = ShiftRequestForm(request.POST)
        form = choosesubordinates(request, form, "base.add_shiftrequest")
        form = include_employee_instance(request, form)
        response = render(
            request,
            "shift_request/htmx/shift_request_create_form.html",
            {"form": form, "f": f},
        )
        if form.is_valid():
            instance = form.save()
            try:
                notify.send(
                    instance.employee_id,
                    recipient=(
                        instance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                    ),
                    verb=f"You have new shift request to approve \
                        for {instance.employee_id}",
                    verb_ar=f"لديك طلب وردية جديد للموافقة عليه لـ {instance.employee_id}",
                    verb_de=f"Sie müssen eine neue Schichtanfrage \
                        für {instance.employee_id} genehmigen",
                    verb_es=f"Tiene una nueva solicitud de turno para \
                        aprobar para {instance.employee_id}",
                    verb_fr=f"Vous avez une nouvelle demande de quart de\
                        travail à approuver pour {instance.employee_id}",
                    icon="information",
                    redirect="/shift-requests/shift-request-view",
                )
            except Exception as e:
                pass
            messages.success(request, _("Request Added"))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "shift_request/htmx/shift_request_create_form.html",
        {"form": form, "f": f},
    )


@login_required
def shift_request_view(request):
    """
    This method renders all shift request instances to a template
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    shift_requests = filtersubordinates(
        request, ShiftRequest.objects.all(), "base.add_shiftrequest"
    )
    shift_requests = shift_requests | ShiftRequest.objects.filter(employee_id=employee)
    f = ShiftRequestFilter()
    form = ShiftRequestForm()
    form = choosesubordinates(
        request,
        form,
        "base.add_shiftrequest",
    )
    form = include_employee_instance(request, form)
    return render(
        request,
        "shift_request/shift_request_view.html",
        {
            "data": paginator_qry(shift_requests, request.GET.get("page")),
            "f": f,
            "form": form,
        },
    )


@login_required
def shift_request_search(request):
    """
    This method is used search shift request by employee and also used to filter shift request.
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    previous_data = request.GET.urlencode()
    f = ShiftRequestFilter(request.GET)
    shift_requests = filtersubordinates(request, f.qs, "base.add_shiftrequest")
    if set(ShiftRequest.objects.filter(employee_id=employee)).issubset(set(f.qs)):
        shift_requests = shift_requests | ShiftRequest.objects.filter(
            employee_id=employee
        )
    shift_requests = sortby(request, shift_requests, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(ShiftRequest, data_dict)
    return render(
        request,
        "shift_request/htmx/requests.html",
        {
            "data": paginator_qry(shift_requests, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
def shift_request_details(request, id):
    """
    This method is used to show shift request details in a modal
    args:
        id : shift request instance id
    """
    shift_request = ShiftRequest.objects.get(id=id)
    return render(
        request,
        "shift_request/htmx/shift_request_detail.html",
        {
            "shift_request": shift_request,
        },
    )


@login_required
@shift_request_change_permission()
def shift_request_update(request, shift_request_id):
    """
    This method is used to update shift request instance
    args:
        id : shift request instance id
    """
    shift_request = ShiftRequest.objects.get(id=shift_request_id)
    form = ShiftRequestForm(instance=shift_request)
    form = choosesubordinates(request, form, "base.change_shiftrequest")
    form = include_employee_instance(request, form)
    if request.method == "POST":
        response = render(
            request,
            "shift_request/request_update_form.html",
            {
                "form": form,
            },
        )
        form = ShiftRequestForm(request.POST, instance=shift_request)
        form = choosesubordinates(request, form, "base.change_shiftrequest")
        form = include_employee_instance(request, form)
        if form.is_valid():
            form.save()
            messages.success(request, _("Request Updated Successfully"))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )

    return render(request, "shift_request/request_update_form.html", {"form": form})


@login_required
def shift_request_cancel(request, id):
    """
    This method is used to update or cancel shift request
    args:
        id : shift request id

    """

    shift_request = ShiftRequest.objects.get(id=id)
    if (
        is_reportingmanger(request, shift_request)
        or request.user.has_perm("base.cancel_shiftrequest")
        or shift_request.employee_id == request.user.employee_get
        and shift_request.approved == False
    ):
        shift_request.canceled = True
        shift_request.approved = False
        shift_request.employee_id.employee_work_info.shift_id = (
            shift_request.previous_shift_id
        )
        shift_request.employee_id.employee_work_info.save()
        shift_request.save()
        messages.success(request, _("Shift request canceled"))
        notify.send(
            request.user.employee_get,
            recipient=shift_request.employee_id.employee_user_id,
            verb="Your shift request has been canceled.",
            verb_ar="تم إلغاء طلبك للوردية.",
            verb_de="Ihr Schichtantrag wurde storniert.",
            verb_es="Se ha cancelado su solicitud de turno.",
            verb_fr="Votre demande de quart a été annulée.",
            redirect="/",
            icon="close",
        )

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You cant cancel the request")


@login_required
@manager_can_enter("base.change_shiftrequest")
@require_http_methods(["POST"])
def shift_request_bulk_cancel(request):
    """
    This method is used to cancel a bunch of shift request.
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    result = False
    for id in ids:
        shift_request = ShiftRequest.objects.get(id=id)
        if (
            is_reportingmanger(request, shift_request)
            or request.user.has_perm("base.cancel_shiftrequest")
            or shift_request.employee_id == request.user.employee_get
            and shift_request.approved == False
        ):
            shift_request.canceled = True
            shift_request.approved = False
            shift_request.employee_id.employee_work_info.shift_id = (
                shift_request.previous_shift_id
            )
            shift_request.employee_id.employee_work_info.save()
            shift_request.save()
            messages.success(request, _("Shift request canceled"))
            notify.send(
                request.user.employee_get,
                recipient=shift_request.employee_id.employee_user_id,
                verb="Your shift request has been canceled.",
                verb_ar="تم إلغاء طلبك للوردية.",
                verb_de="Ihr Schichtantrag wurde storniert.",
                verb_es="Se ha cancelado su solicitud de turno.",
                verb_fr="Votre demande de quart a été annulée.",
                redirect="/",
                icon="close",
            )
            result = True
    return JsonResponse({"result": result})


@login_required
@manager_can_enter("base.change_shiftrequest")
def shift_request_approve(request, id):
    """
    This method is used to approve shift request
    args:
        id : shift request instance id
    """

    shift_request = ShiftRequest.objects.get(id=id)

    if (
        is_reportingmanger(request, shift_request)
        or request.user.has_perm("approve_shiftrequest")
        or request.user.has_perm("change_shiftrequest")
        and not shift_request.approved
    ):
        """
        here the request will be approved, can send mail right here
        """

        if not shift_request.is_any_request_exists():
            shift_request.approved = True
            shift_request.canceled = False
            shift_request.save()
            messages.success(request, _("Shift has been approved."))
            notify.send(
                request.user.employee_get,
                recipient=shift_request.employee_id.employee_user_id,
                verb="Your shift request has been approved.",
                verb_ar="تمت الموافقة على طلبك للوردية.",
                verb_de="Ihr Schichtantrag wurde genehmigt.",
                verb_es="Se ha aprobado su solicitud de turno.",
                verb_fr="Votre demande de quart a été approuvée.",
                redirect="/",
                icon="checkmark",
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        else:
            messages.error(
                request, _("A shift request already exists during this time period.")
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You Dont Have Permission")


@login_required
@require_http_methods(["POST"])
@manager_can_enter("base.change_shiftrequest")
def shift_request_bulk_approve(request):
    """
    This method is used to approve a bunch of shift request
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    result = False
    for id in ids:
        shift_request = ShiftRequest.objects.get(id=id)
        if (
            is_reportingmanger(request, shift_request)
            or request.user.has_perm("approve_shiftrequest")
            or request.user.has_perm("change_shiftrequest")
            and not shift_request.approved
        ):
            """
            here the request will be approved, can send mail right here
            """
            shift_request.approved = True
            shift_request.canceled = False
            employee_work_info = shift_request.employee_id.employee_work_info
            employee_work_info.shift_id = shift_request.shift_id
            employee_work_info.save()
            shift_request.save()
            messages.success(request, _("Shifts have been approved."))
            notify.send(
                request.user.employee_get,
                recipient=shift_request.employee_id.employee_user_id,
                verb="Your shift request has been approved.",
                verb_ar="تمت الموافقة على طلبك للوردية.",
                verb_de="Ihr Schichtantrag wurde genehmigt.",
                verb_es="Se ha aprobado su solicitud de turno.",
                verb_fr="Votre demande de quart a été approuvée.",
                redirect="/",
                icon="checkmark",
            )
        result = True
    return JsonResponse({"result": result})


@login_required
@require_http_methods(["POST"])
def shift_request_delete(request, id):
    """
    This method is used to delete shift request instance
    args:
        id : shift request instance id

    """
    try:
        shift_request = ShiftRequest.objects.get(id=id)
        user = shift_request.employee_id.employee_user_id
        messages.success(request, "Shift request deleted")
        shift_request.delete()
        notify.send(
            request.user.employee_get,
            recipient=user,
            verb="Your shift request has been deleted.",
            verb_ar="تم حذف طلب الوردية الخاص بك.",
            verb_de="Ihr Schichtantrag wurde gelöscht.",
            verb_es="Se ha eliminado su solicitud de turno.",
            verb_fr="Votre demande de quart a été supprimée.",
            redirect="/",
            icon="trash",
        )

    except ShiftRequest.DoesNotExist:
        messages.error(request, _("Shift request not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this shift request."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("delete_shiftrequest")
@require_http_methods(["POST"])
def shift_request_bulk_delete(request):
    """
    This method is used to delete shift request instance
    args:
        id : shift request instance id

    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    result = False
    for id in ids:
        try:
            shift_request = ShiftRequest.objects.get(id=id)
            user = shift_request.employee_id.employee_user_id
            shift_request.delete()
            messages.success(request, _("Shift request deleted."))
            notify.send(
                request.user.employee_get,
                recipient=user,
                verb="Your shift request has been deleted.",
                verb_ar="تم حذف طلب الوردية الخاص بك.",
                verb_de="Ihr Schichtantrag wurde gelöscht.",
                verb_es="Se ha eliminado su solicitud de turno.",
                verb_fr="Votre demande de quart a été supprimée.",
                redirect="/",
                icon="trash",
            )
        except ShiftRequest.DoesNotExist:
            messages.error(request, _("Shift request not found."))
        except ProtectedError:
            messages.error(
                request,
                _(
                    "You cannot delete {employee} shift request for the date {date}."
                ).format(
                    employee=shift_request.employee_id,
                    date=shift_request.requested_date,
                ),
            )
        result = True
    return JsonResponse({"result": result})


@login_required
def notifications(request):
    """
    This method will render notification items
    """
    all_notifications = request.user.notifications.unread()
    return render(
        request,
        "notification/notification_items.html",
        {"notifications": all_notifications},
    )


@login_required
def clear_notification(request):
    """
    This method is used to clear notification
    """
    try:
        request.user.notifications.read().delete()
        messages.success(request, _("Unread notifications removed."))
    except Exception as e:
        messages.error(request, e)
    notifications = request.user.notifications.unread()
    return render(
        request,
        "notification/notification_items.html",
        {"notifications": notifications},
    )


@login_required
def delete_notification(request, id):
    """
    This method is used to delete notification
    """
    try:
        request.user.notifications.get(id=id).delete()
        messages.success(request, _("Notification deleted."))
    except Exception as e:
        messages.error(request, e)
    notifications = request.user.notifications.all()
    return render(
        request, "notification/all_notifications.html", {"notifications": notifications}
    )


@login_required
def read_notifications(request):
    """
    This method is to mark as read the notification
    """
    try:
        request.user.notifications.all().mark_all_as_read()
        messages.info(request, _("Notifications marked as read"))
    except Exception as e:
        messages.error(request, e)
    notifications = request.user.notifications.unread()

    return render(
        request,
        "notification/notification_items.html",
        {"notifications": notifications},
    )


@login_required
def all_notifications(request):
    """
    This method to render all notifications to template
    """
    return render(
        request,
        "notification/all_notifications.html",
        {"notifications": request.user.notifications.all()},
    )


@login_required
@permission_required("payroll.view_settings")
def settings(request):
    """
    This method is used to render settings template
    """
    instance = PayrollSettings.objects.first()
    form = PayrollSettingsForm(instance=instance)
    if request.method == "POST":
        form = PayrollSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Payroll settings updated."))
    return render(request, "payroll/settings/payroll_settings.html", {"form": form})


@login_required
@permission_required("attendance.add_attendancevalidationcondition")
def validation_condition_create(request):
    """
    This method render a form to create attendance validation conditions,
    and create if the form is valid.
    """
    form = AttendanceValidationConditionForm()
    if request.method == "POST":
        form = AttendanceValidationConditionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance Break-point settings created."))
    condition = AttendanceValidationCondition.objects.first()
    return render(
        request,
        "attendance/break_point/condition.html",
        {"form": form, "condition": condition},
    )


@login_required
@permission_required("attendance.change_attendancevalidationcondition")
def validation_condition_update(request, obj_id):
    """
    This method is used to update validation condition
    Args:
        obj_id : validation condition instance id
    """
    condition = AttendanceValidationCondition.objects.get(id=obj_id)
    form = AttendanceValidationConditionForm(instance=condition)
    if request.method == "POST":
        form = AttendanceValidationConditionForm(request.POST, instance=condition)
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance Break-point settings updated."))
    return render(
        request,
        "attendance/break_point/condition.html",
        {"form": form, "condition": condition},
    )
