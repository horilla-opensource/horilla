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
        self.check_fields = [
            "employee_id",
            "requested_employee_id",
        ]

    def get_queryset(self):
        """
        get_queryset method
        """
        from horilla.decorators import logger

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
            logger.error(e)
        try:
            has_duplicates = queryset.count() != queryset.distinct().count()
            if has_duplicates:
                queryset = queryset.distinct()
        except:
            pass
        return queryset

    def all(self):
        """
        Override the all() method
        """
        queryset = []
        try:
            queryset = self.get_queryset()
            if queryset.exists():
                try:
                    model_name = queryset.model._meta.model_name
                    if model_name == "employee":
                        queryset = queryset.filter(is_active=True)
                    else:
                        for field in queryset.model._meta.fields:
                            if isinstance(field, models.ForeignKey):
                                if field.name in self.check_fields:
                                    related_model_is_active_filter = {
                                        f"{field.name}__is_active": True
                                    }
                                    queryset = queryset.filter(
                                        **related_model_is_active_filter
                                    )
                except:
                    pass
        except:
            pass
        return queryset
