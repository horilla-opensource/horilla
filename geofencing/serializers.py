from geopy.geocoders import Nominatim
from rest_framework import serializers

from .models import GeoFencing


class GeoFencingSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoFencing
        fields = "__all__"

    def validate(self, data):
        geolocator = Nominatim(user_agent="geo_checker")  # Use a unique user-agent
        start = data.get("start")
        if start:
            try:
                latitude = data.get("latitude")
                longitude = data.get("longitude")
                location = geolocator.reverse((latitude, longitude), exactly_one=True)
                if not location:
                    raise serializers.ValidationError("Invalid Location")
            except Exception as e:
                raise serializers.ValidationError(e)
        return data


class EmployeeLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoFencing
        fields = ["latitude", "longitude"]
