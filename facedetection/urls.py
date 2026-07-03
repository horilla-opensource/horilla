from django.urls import path

from .views import *

urlpatterns = [
    path("config/", FaceDetectionConfigAPIView.as_view()),
    path("setup/", EmployeeFaceDetectionGetPostAPIView.as_view()),
    path("toggle/", enable_disable_face_detection, name="face-detection-toggle"),
    path("", face_detection_config, name="face-config"),
]
