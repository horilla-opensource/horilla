"""
horilla/signals.py
"""

from django.dispatch import Signal, receiver

pre_bulk_update = Signal()
post_bulk_update = Signal()
