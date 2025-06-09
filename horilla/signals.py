"""
horilla/signals.py
"""

from django.dispatch import Signal

pre_bulk_update = Signal()
post_bulk_update = Signal()

pre_model_clean = Signal()
post_model_clean = Signal()

pre_scheduler = Signal()
post_scheduler = Signal()

pre_generic_delete = Signal()
post_generic_delete = Signal()

pre_generic_import = Signal()
post_generic_import = Signal()
