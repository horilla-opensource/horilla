from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser

from .models import Candidate


class CandidateAuthenticationBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            candidate = Candidate.objects.get(email=username, mobile=password)
            return candidate
        except Candidate.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Candidate.objects.get(pk=user_id)
        except Candidate.DoesNotExist:
            return AnonymousUser()
