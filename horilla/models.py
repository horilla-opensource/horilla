"""
models.py
=========

This module defines the abstract base model `HorillaModel` for the Horilla HRMS project.
The `HorillaModel` provides common fields and functionalities for other models within
the application, such as tracking creation and modification timestamps and user
information, audit logging, and active/inactive status management.
"""

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.contrib.auth.models import User
from django.db import models
from django.db.models.fields.files import FieldFile
from django.urls import reverse
from django.utils.translation import gettext as _

from horilla.horilla_middlewares import _thread_locals


@property
def url(self: FieldFile):
    """
    Custom url attribute/property
    """
    try:
        self._require_file()
    except Exception as e:
        return reverse("404")
    return self.storage.url(self.name)


setattr(FieldFile, "url", url)


class HorillaModel(models.Model):
    """
    An abstract base model that includes common fields and functionalities
    for models within the Horilla application.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name=_("Created At"),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Created By"),
    )

    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Modified By"),
        related_name="%(class)s_modified_by",
    )
    horilla_history = AuditlogHistoryField()
    objects = models.Manager()
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        """
        Meta class for HorillaModel
        """

        abstract = True

    def save(self, *args, **kwargs):
        """
        Override the save method to automatically set the created_by and
        modified_by fields based on the current request user.
        """
        request = getattr(_thread_locals, "request", None)

        if request:
            user = request.user

            if (
                hasattr(self, "created_by")
                and hasattr(self._meta.get_field("created_by"), "related_model")
                and self._meta.get_field("created_by").related_model == User
            ):
                if request and not self.pk:
                    if user.is_authenticated:
                        self.created_by = user

            if request and not request.user.is_anonymous:
                self.modified_by = user

        super(HorillaModel, self).save(*args, **kwargs)

    @classmethod
    def find(cls, object_id):
        """
        Find an object of this class by its ID.
        """
        try:
            obj = cls.objects.filter(id=object_id).first()
            return obj
        except Exception as e:
            # Log the exception if needed
            return None

    @classmethod
    def activate_deactivate(cls, object_id):
        """
        Toggle the is_active status of an object of this class.
        """
        obj = cls.find(object_id)
        if obj:
            obj.is_active = not obj.is_active
            obj.save()


auditlog.register(HorillaModel, serialize_data=True)
