"""Template utilities: syntax checking."""

from django.template import Template, TemplateSyntaxError


def check_template_syntax(template):
    """
    Check if template content is valid Django template syntax.

    Returns:
        (True, None) if valid, (False, exception message) if invalid.
    """
    try:
        Template(template.content)
        return (True, None)
    except TemplateSyntaxError as e:
        return (False, str(e))
