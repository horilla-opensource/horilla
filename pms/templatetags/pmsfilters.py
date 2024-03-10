from django.template.defaultfilters import register

from pms.models import Objective


@register.filter(name="replace")
def replace(string):
    """
    This method is used to return str of the fk fields
    """

    return string.replace("_", " ")


@register.filter(name="kr_count")
def kr_count(objective_id):
    objective = Objective.objects.get(id=objective_id)
    empl_objectives = objective.employee_objective.all()
    kr_list = []
    for obj in empl_objectives:
        for kr in obj.employee_key_result.all():
            kr_list.append(kr)
    return kr_list
