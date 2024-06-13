"""
horilla_automations/methods/methods.py

"""

import operator

from django.core.exceptions import FieldDoesNotExist
from django.http import QueryDict

from employee.models import Employee
from horilla.models import HorillaModel
from recruitment.models import Candidate


def get_related_models(model: HorillaModel) -> list:
    related_models = []
    for field in model._meta.get_fields():
        if field.one_to_many or field.one_to_one or field.many_to_many:
            related_model = field.related_model
            related_models.append(related_model)
    return related_models


def generate_choices(model_path):
    module_name, class_name = model_path.rsplit(".", 1)

    module = __import__(module_name, fromlist=[class_name])
    model_class: Employee = getattr(module, class_name)

    to_fields = []
    mail_details_choice = []

    for field in list(model_class._meta.fields) + list(model_class._meta.many_to_many):
        related_model = field.related_model
        if related_model in [Candidate, Employee]:
            email_field = (
                f"{field.name}__get_email",
                f"{field.verbose_name.capitalize().replace(' id','')} mail field ",
            )
            mail_detail = (
                f"{field.name}__pk",
                field.verbose_name.capitalize().replace(" id", ""),
            )
            if field.related_model == Employee:
                to_fields.append(
                    (
                        f"{field.name}__employee_work_info__reporting_manager_id__get_email",
                        f"{field.verbose_name.capitalize().replace(' id','')}'s reporting manager",
                    )
                )
                mail_details_choice.append(
                    (
                        f"{field.name}__employee_work_info__reporting_manager_id__pk",
                        f"{field.verbose_name.capitalize().replace(' id','')}'s reporting manager",
                    )
                )

            to_fields.append(email_field)
            mail_details_choice.append(mail_detail)
    if model_class in [Candidate, Employee]:
        to_fields.append(
            (
                "get_email",
                f"{model_class.__name__}'s mail",
            )
        )
        mail_details_choice.append(("pk", model_class.__name__))

    to_fields = list(set(to_fields))
    return to_fields, mail_details_choice, model_class


def get_model_class(model_path):
    """
    method to return the model class from string 'app.models.Model'
    """
    module_name, class_name = model_path.rsplit(".", 1)

    module = __import__(module_name, fromlist=[class_name])
    model_class: Employee = getattr(module, class_name)
    return model_class


operator_map = {
    "==": operator.eq,
    "!=": operator.ne,
    "and": lambda x, y: x and y,
    "or": lambda x, y: x or y,
}


def querydict(query_string):
    query_dict = QueryDict(query_string)
    return query_dict


def split_query_string(query_string):
    """
    Split the query string based on the "&logic=" substring
    """
    query_parts = query_string.split("&logic=")
    result = []

    for i, part in enumerate(query_parts):
        if i != 0:
            result.append(querydict("&logic=" + part))
        else:
            result.append(querydict(part))
    return result


def evaluate_condition(value1, operator_str, value2):
    op_func = operator_map.get(operator_str)
    if op_func is None:
        raise ValueError(f"Invalid operator: {operator_str}")
    return op_func(value1, value2)


def get_related_field_model(model: Employee, field_path):
    parts = field_path.split("__")
    for part in parts:
        # Handle the special case for 'pk'
        if part == "pk":
            field = model._meta.pk
        else:
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                # Handle the case where the field does not exist
                raise

        if field.is_relation:
            model = field.related_model
        else:
            # If the part is a non-relation field, break the loop
            break
    return model
