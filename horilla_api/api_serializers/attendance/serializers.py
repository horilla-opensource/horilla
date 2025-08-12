from rest_framework import serializers

from attendance.models import *
from base.models import HorillaMailTemplate


class AttendanceSerializer(serializers.ModelSerializer):
    employee_first_name = serializers.CharField(
        source="employee_id.employee_first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee_id.employee_last_name", read_only=True
    )
    shift_name = serializers.CharField(source="shift_id.employee_shift", read_only=True)
    badge_id = serializers.CharField(source="employee_id.badge_id", read_only=True)
    employee_profile_url = serializers.SerializerMethodField(read_only=True)
    work_type = serializers.CharField(source="work_type_id.work_type", read_only=True)

    class Meta:
        model = Attendance
        exclude = [
            "overtime_second",
            "at_work_second",
            "attendance_day",
            "request_description",
            "approved_overtime_second",
            "request_type",
            "requested_data",
            "is_validate_request",
            "is_validate_request_approved",
            "attendance_overtime",
        ]

    def validate(self, data):
        # Check if attendance exists for the employee on the current date
        if self.instance:
            return data
        employee_id = data.get("employee_id")
        attendance_date = data.get("attendance_date", date.today())
        if Attendance.objects.filter(
            employee_id=employee_id, attendance_date=attendance_date
        ).exists():
            raise ValidationError(
                ("Attendance for this employee on the current date already exists.")
            )
        return data

    def get_employee_profile_url(self, obj):
        try:
            employee_profile = obj.employee_id.employee_profile
            return employee_profile.url
        except:
            return None


class AttendanceRequestSerializer(serializers.ModelSerializer):
    employee_first_name = serializers.CharField(
        source="employee_id.employee_first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee_id.employee_last_name", read_only=True
    )
    shift_name = serializers.CharField(source="shift_id.employee_shift", read_only=True)
    badge_id = serializers.CharField(source="employee_id.badge_id", read_only=True)
    employee_profile_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Attendance
        exclude = [
            "attendance_overtime",
            "attendance_overtime_approve",
            "attendance_validated",
            "approved_overtime_second",
            "is_validate_request",
            "is_validate_request_approved",
            "request_type",
            "created_at",
        ]

    def create(self, validated_data):
        # Extract relevant data from validated_data
        employee_id = validated_data.get("employee_id")
        attendance_date = validated_data.get("attendance_date")
        # Check if attendance exists for the employee and date
        attendances = Attendance.objects.filter(
            employee_id=employee_id, attendance_date=attendance_date
        )
        data = {
            "employee_id": validated_data.get("employee_id"),
            "attendance_date": validated_data.get("attendance_date"),
            "attendance_clock_in_date": validated_data.get("attendance_clock_in_date"),
            "attendance_clock_in": validated_data.get("attendance_clock_in"),
            "attendance_clock_out": validated_data.get("attendance_clock_out"),
            "attendance_clock_out_date": validated_data.get(
                "attendance_clock_out_date"
            ),
            "shift_id": validated_data.get("shift_id"),
            "work_type_id": validated_data.get("work_type_id"),
            "attendance_worked_hour": validated_data.get("attendance_worked_hour"),
            "minimum_hour": validated_data.get("minimum_hour"),
        }
        if attendances.exists():
            data["employee_id"] = employee_id.id
            data["attendance_date"] = str(attendance_date)
            data["attendance_clock_in_date"] = self.data["attendance_clock_in_date"]
            data["attendance_clock_in"] = self.data["attendance_clock_in"]
            data["attendance_clock_out"] = (
                None
                if data["attendance_clock_out"] == "None"
                else data["attendance_clock_out"]
            )
            data["attendance_clock_out_date"] = (
                None
                if data["attendance_clock_out_date"] == "None"
                else data["attendance_clock_out_date"]
            )
            data["work_type_id"] = self.data["work_type_id"]
            data["shift_id"] = self.data["shift_id"]
            attendance = attendances.first()
            for key, value in data.items():
                data[key] = str(value)
            attendance.requested_data = json.dumps(data)
            attendance.is_validate_request = True
            if attendance.request_type != "create_request":
                attendance.request_type = "update_request"
            attendance.request_description = self.data["request_description"]
            return attendance.save()
        new_instance = Attendance(**data)
        new_instance.is_validate_request = True
        new_instance.attendance_validated = False
        new_instance.request_description = self.data["request_description"]
        new_instance.request_type = "create_request"
        new_instance.save()
        return new_instance

    def update(self, instance, validated_data):
        if "employee_id" in validated_data:
            validated_data.pop("employee_id")
        return super().update(instance, validated_data)

    def get_employee_profile_url(self, obj):
        try:
            employee_profile = obj.employee_id.employee_profile
            return employee_profile.url
        except:
            return None


class AttendanceOverTimeSerializer(serializers.ModelSerializer):
    badge_id = serializers.CharField(source="employee_id.badge_id", read_only=True)
    employee_first_name = serializers.CharField(
        source="employee_id.employee_first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee_id.employee_last_name", read_only=True
    )
    employee_profile_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AttendanceOverTime
        fields = [
            "id",
            "employee_first_name",
            "employee_last_name",
            "employee_profile_url",
            "badge_id",
            "employee_id",
            "month",
            "year",
            "worked_hours",
            "pending_hours",
            "overtime",
        ]

    def get_employee_profile_url(self, obj):
        try:
            employee_profile = obj.employee_id.employee_profile
            return employee_profile.url
        except:
            return None


class AttendanceLateComeEarlyOutSerializer(serializers.ModelSerializer):
    employee_first_name = serializers.CharField(
        source="employee_id.employee_first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee_id.employee_last_name", read_only=True
    )

    class Meta:
        model = AttendanceLateComeEarlyOut
        fields = "__all__"


class AttendanceActivitySerializer(serializers.ModelSerializer):
    employee_first_name = serializers.CharField(
        source="employee_id.employee_first_name", read_only=True
    )
    employee_last_name = serializers.CharField(
        source="employee_id.employee_last_name", read_only=True
    )

    class Meta:
        model = AttendanceActivity
        fields = "__all__"


class MailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorillaMailTemplate
        fields = "__all__"


class UserAttendanceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            "id",
            "attendance_date",
            "attendance_clock_in",
            "attendance_clock_out",
            "attendance_worked_hour",
        ]


class UserAttendanceDetailedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = "__all__"
