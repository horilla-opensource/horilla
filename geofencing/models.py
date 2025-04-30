from django.core.exceptions import ValidationError
from django.db import models
from geopy.geocoders import Nominatim

from base.models import Company


class GeoFencing(models.Model):
    latitude = models.FloatField(max_length=100)
    longitude = models.FloatField(max_length=100)
    radius_in_meters = models.IntegerField()
    company_id = models.OneToOneField(
        "base.Company",
        related_name="geo_fencing",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    start = models.BooleanField(default=False)

    def clean(self):
        geolocator = Nominatim(user_agent="geo_checker")  # Use a unique user-agent
        try:
            location = geolocator.reverse(
                (self.latitude, self.longitude), exactly_one=True
            )
            if location:
                pass
            else:
                raise ValidationError("Invalid Location")
        except Exception as e:
            raise ValidationError(e)
        return super().clean()

    def save_base(
        self, raw=..., force_insert=..., force_update=..., using=..., update_fields=...
    ):
        self.clean()
        return super().save_base(raw, force_insert, force_update, using, update_fields)
