"""
horilla_company_manager.py
"""

import logging
from typing import Coroutine, Sequence

from django.db import models
from django.db.models.query import QuerySet

from horilla.horilla_middlewares import _thread_locals
from horilla.signals import post_bulk_update, pre_bulk_update

logger = logging.getLogger(__name__)
django_filter_update = QuerySet.update


def update(self, *args, **kwargs):
    # pre_update signal
    request = getattr(_thread_locals, "request", None)
    self.request = request
    pre_bulk_update.send(sender=self.model, queryset=self, args=args, kwargs=kwargs)
    result = django_filter_update(self, *args, **kwargs)
    # post_update signal
    post_bulk_update.send(sender=self.model, queryset=self, args=args, kwargs=kwargs)

    return result


setattr(QuerySet, "update", update)


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
                        request = getattr(_thread_locals, "request", None)
                        if not getattr(request, "is_filtering", None):
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

    def filter(self, *args, **kwargs):
        queryset = super().filter(*args, **kwargs)
        setattr(_thread_locals, "queryset_filter", queryset)
        return queryset

    def entire(self):
        """
        Fetch all datas from a model without applying any company filter.
        """
        queryset = super().get_queryset()
        return queryset  # No filtering applied
