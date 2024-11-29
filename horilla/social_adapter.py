from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from employee.models import Employee


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")
        try:
            user = User.objects.get(email=email)
            sociallogin.user = user
        except User.DoesNotExist:
            user = super().save_user(request, sociallogin)
            full_name = sociallogin.account.extra_data.get("name", "")
            first_name, last_name = full_name.split() if " " in full_name else (full_name, "")

            employee = Employee(
                employee_user_id=user,
                employee_first_name=first_name,
                employee_last_name=last_name,
                email=email,
            )
            employee.save()