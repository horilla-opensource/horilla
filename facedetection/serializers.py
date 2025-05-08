from rest_framework import serializers

from .models import *


class EmployeeFaceDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeFaceDetection
        fields = "__all__"
