from rest_framework import serializers

from employee.models import Employee


class GetEmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "full_name", "employee_profile"]

    def get_full_name(self, obj):
        return obj.get_full_name()
