"""
This page is handling the cbv methods of mail log tab in employee individual page.
"""

from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.cbv.mail_log_tab import MailLogTabList
from horilla_views.generic.cbv.views import HorillaListView
from recruitment.models import Candidate


class CandidateMailLogTabList(MailLogTabList):
    """
    list view for mail log tab in candidate
    """

    def get_context_data(self, **kwargs: Any):
        """
        Adds a search URL to the context based on the candidate's primary key.
        """
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["search_url"] = (
            f"{reverse('candidate-mail-log-list',kwargs={'pk': pk})}"
        )
        return context

    def get_queryset(self):
        """
        Returns a filtered and ordered queryset of email logs for the specified candidate.
        """

        # queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        candidate_obj = Candidate.objects.get(id=pk)
        return (
            HorillaListView.get_queryset(self)
            .filter(to__icontains=candidate_obj.email)
            .order_by("-created_at")
        )
