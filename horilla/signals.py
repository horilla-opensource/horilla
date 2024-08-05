"""
horilla/signals.py
"""

from django.dispatch import Signal

pre_bulk_update = Signal()
post_bulk_update = Signal()
