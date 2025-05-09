from django.urls import path

from .views import *

urlpatterns = [
    path("setup/", GeoFencingSetupGetPostAPIView.as_view()),
    path("setup/<int:pk>/", GeoFencingSetupPutDeleteAPIView.as_view()),
    path("setup-check/", GeoFencingSetUpPermissionCheck.as_view()),
    path("location-check/", GeoFencingEmployeeLocationCheckAPIView.as_view()),
    path("config/", geo_location_config, name="geo-config"),
]
