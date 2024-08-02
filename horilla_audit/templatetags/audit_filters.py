from django.template.defaultfilters import register


@register.filter(name="fk_history")
def fk_history(instance, change):
    """
    This method is used to return str of the fk fields
    """
    value = "Deleted"
    try:
        value = getattr(instance, change["field_name"])
    except:
        value = instance.__dict__[change["field_name"] + "_id"]
        value = str(value) + f" (Previous {change['field']} deleted)"
        pass
    return value


@register.filter(name="verbose_name")
def verbose_name(model, field_name=None):
    """ "
    This method is used to fine the verbose name of a field
    """
    if not field_name:
        model_name = model._meta.verbose_name.capitalize()
        return model_name

    try:
        field = model._meta.get_field(field_name)
        return field.verbose_name
    except:
        return field_name
