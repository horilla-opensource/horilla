from django.urls import path

from .views import *

urlpatterns = [
    path("config/", FaceDetectionConfigAPIView.as_view()),
    path("setup/", EmployeeFaceDetectionGetPostAPIView.as_view()),
    path("", face_detection_config, name="face-config"),
]
