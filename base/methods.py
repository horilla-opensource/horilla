from employee.models import Employee
from django.utils.translation import gettext as _


def filtersubordinates(request, queryset, perm=None):
    """
    This method is used to filter out subordinates queryset element.
    """
    user = request.user
    if user.has_perm(perm):
        return queryset
    manager = Employee.objects.filter(employee_user_id=user).first()
    queryset = queryset.filter(
        employee_id__employee_work_info__reporting_manager_id=manager
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
    if sortby is not None and sortby != "":
        # here will update the orderingList
        ordering["field"] = sortby
        if queryset.query.order_by == queryset.query.order_by:
            queryset = queryset.order_by(f'{ordering["ordering"]}{sortby}')
        if ordering["ordering"] == "-":
            ordering["ordering"] = ""
        else:
            ordering["ordering"] = "-"
        orderingList = [item for item in orderingList if item["id"] != id]
        orderingList.append(ordering)

    return queryset