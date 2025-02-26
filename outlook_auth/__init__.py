"""
outlook_auth/__init__.py
"""

from django.conf import settings

from outlook_auth import scheduler as _scheduler

settings.OUTLOOK_SCOPES = ["https://outlook.office.com/SMTP.Send"]

# Add these in horilla/settings.py

"""

installed_apps = [
    ...
    'outlook_auth',
    ...
]

EMAIL_BACKEND = 'outlook_auth.backends.OutlookBackend'

"""
# NOTE: Horilla should be run in https

# Please add redircet url in Azure app authentication URi and AzureApi model redirect URi

"""

https://<your_domain.com>/outlook/callback

"""
