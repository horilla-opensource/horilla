from django import template

register = template.Library()


@register.filter(name="yes_no")
def yesno(value):
    return "Yes" if value else "No"

@register.filter(name="on_off")
def on_off(value):
    if value == "on":
        return "Yes"
    elif value == "off":
        return "No"
