"""
paginator_qry.py

This module is used to pagination
"""

from django.core.paginator import Paginator

from base.methods import get_pagination


def paginator_qry(qryset, page_number):
    """
    This method is used to generate common paginator limit.
    """
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset
