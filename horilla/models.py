from django.db import models
from django.contrib.auth.models import User
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
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if (
            hasattr(self, "created_by")
            and hasattr(self._meta.get_field("created_by"), "related_model")
            and self._meta.get_field("created_by").related_model == User
        ):
            request = getattr(_thread_locals, "request", None)
            if request and not self.pk:
                user = request.user
                if user.is_authenticated:
                    self.created_by = user
        super(HorillaModel, self).save(*args, **kwargs)

    @classmethod
    def find(cls, object_id):
        # object_id = 1020
        return cls.objects.filter(id=object_id).first()
    
    @classmethod
    def activate_deactivate(cls, object_id):       
        object = cls.find(object_id)
        if object:
            object.is_active = not object.is_active
            object.save()
