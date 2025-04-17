"""
dynamic_fields/signals.py
"""

from django.core.management import call_command
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from dynamic_fields.models import DynamicField


@receiver(pre_delete, sender=DynamicField)
def pre_delete_dynamic_field(sender, instance, **kwargs):
    """
    method to delete the column from the db before
    deleting the dynamic field
    """
    call_command("delete_field", *(instance.pk,))
