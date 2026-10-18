from datetime import date

from django.test import TestCase

from attendance.models import WorkRecords
from base.models import Company
from employee.models import Employee

# The German translation of the half-day message is 40 characters.
LONG_TRANSLATED_MESSAGE = "HalbtagesTeilnahme muss validiert werden"


class WorkRecordMessageLengthTests(TestCase):
    """
    WorkRecords.message holds a translated note. At max_length=30 a translated
    half-day message overflowed the column and PostgreSQL raised DataError.
    """

    def test_a_translated_message_longer_than_30_characters_saves(self):
        self.assertGreater(len(LONG_TRANSLATED_MESSAGE), 30)
        Company.objects.create(
            company="Probe", address="a", country="c", state="s", city="x", zip="1"
        )
        employee = Employee.objects.create(
            employee_first_name="P",
            employee_last_name="Q",
            email="probe@example.test",
            phone="1",
        )
        record = WorkRecords.objects.create(
            employee_id=employee,
            date=date(2026, 10, 1),
            message=LONG_TRANSLATED_MESSAGE,
            work_record_type="HDP",
        )
        record.refresh_from_db()
        self.assertEqual(record.message, LONG_TRANSLATED_MESSAGE)
