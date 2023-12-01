"""
horilla_company_manager.py
"""
import threading
from django.db import models
from base.thread_local_middleware import _thread_locals


class HorillaCompanyManager(models.Manager):
    """
    HorillaCompanyManager
    """

    def __init__(self, related_company_field=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_company_field = related_company_field

    def get_queryset(self):
        """
        get_queryset method
        """
        queryset = super().get_queryset()
        request = getattr(_thread_locals, "request", None)
        selected_company = None
        if request is not None:
            selected_company = request.session.get("selected_company")
        try:
            queryset = (
                queryset.filter(self.model.company_filter)
                if selected_company != "all" and selected_company
                else queryset
            )
        except Exception as e:
            print(e)
        try:
            has_duplicates = queryset.count() != queryset.distinct().count()
            if has_duplicates:
                queryset = queryset.distinct()
        except:
            pass
        return queryset
