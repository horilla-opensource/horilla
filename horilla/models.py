from django.db import models
from django.contrib.auth.models import User


class HorillaModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        request = kwargs.get("request", None)
        if request and not self.pk:
            user = request.user
            if user.is_authenticated:
                self.created_by = user
        request = kwargs.pop("request", None)
        super(HorillaModel, self).save(*args, **kwargs)
