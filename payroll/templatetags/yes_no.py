from django import template

register = template.Library()


@register.filter(name="yes_no")
def yesno(value):
    return "Yes" if value else "No"
