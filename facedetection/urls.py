from django.urls import path

from .views import *

urlpatterns = [path("setup/", FaceDetectionGetPostAPIView.as_view())]
