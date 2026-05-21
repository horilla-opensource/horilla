import re

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser

from .models import Candidate


def _normalize_phone(value):
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


class CandidateAuthenticationBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        email = (username or "").strip().lower()
        phone = _normalize_phone(password)
        if not email or not phone:
            return None

        candidates = Candidate.objects.filter(email__iexact=email)
        for candidate in candidates:
            candidate_phone = _normalize_phone(candidate.mobile)
            if not candidate_phone:
                continue

            if candidate_phone == phone or candidate_phone[-10:] == phone[-10:]:
                return candidate
        return None

    def get_user(self, user_id):
        try:
            return Candidate.objects.get(pk=user_id)
        except Candidate.DoesNotExist:
            return AnonymousUser()
