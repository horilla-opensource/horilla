from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect

from base.models import AllowedDomains
from employee.models import Employee


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    @staticmethod
    def is_domain_valid(domain_objects, email):
        if domain_objects.exists():
            domain_records = domain_objects.values('domains')[0]
            domains = domain_records['domains']
            if domains:
                domain_list = domains.split(",")
                email_domain = email.split('@')[1]
                if email_domain in domain_list:
                    return True
        return False

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")
        if not self.is_domain_valid(AllowedDomains.objects, email):
            messages.error(request, "The domain you tried to login with is not supported by the system!")
            raise ImmediateHttpResponse(redirect('login'))
        else:
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


