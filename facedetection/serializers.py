from rest_framework import serializers

from .models import *


class FaceDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceDetection
        fields = "__all__"


class EmployeeFaceDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeFaceDetection
        fields = "__all__"
