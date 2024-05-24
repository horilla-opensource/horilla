from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext as _

from base.thread_local_middleware import _thread_locals


class HorillaModel(models.Model):
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
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", None)
        # also here will have scheduled activities
        # at the time there will no change to the modified user,
        # its remains same as previous
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
        try:
            object = cls.objects.filter(id=object_id).first()
            return object
        except:
            return None

    @classmethod
    def activate_deactivate(cls, object_id):
        object = cls.find(object_id)
        if object:
            object.is_active = not object.is_active
            object.save()


auditlog.register(HorillaModel, serialize_data=True)
