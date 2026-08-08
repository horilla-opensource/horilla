"""Biometric device model / validator smoke tests."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from biometric.models import BiometricDevices, validate_schedule_time_format
from horilla.testkit import make_company


class ScheduleTimeFormatTests(TestCase):
    def test_valid_hhmm(self):
        validate_schedule_time_format("01:30")  # no raise

    def test_rejects_zero_duration(self):
        with self.assertRaises(ValidationError):
            validate_schedule_time_format("00:00")

    def test_rejects_bad_format(self):
        with self.assertRaises(ValidationError):
            validate_schedule_time_format("not-a-time")

    def test_rejects_invalid_minute(self):
        with self.assertRaises(ValidationError):
            validate_schedule_time_format("01:60")


class BiometricDeviceCreateTests(TestCase):
    def test_create_zk_device(self):
        company = make_company("Bio Co")
        device = BiometricDevices.objects.create(
            name="Front Desk ZK",
            machine_type="zk",
            machine_ip="192.168.1.10",
            port=4370,
            company_id=company,
        )
        self.assertIsNotNone(device.pk)
        self.assertEqual(device.machine_type, "zk")
        self.assertFalse(device.is_live)
