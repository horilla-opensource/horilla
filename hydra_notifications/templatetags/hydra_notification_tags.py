from django import template

from hydra_notifications.services import preference_for_user


register = template.Library()


@register.simple_tag(takes_context=True)
def hydra_notification_preferences(context):
    request = context.get("request")
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return preference_for_user(user=user)
