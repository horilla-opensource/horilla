"""Smoke tests that shared testkit factories work against the live schema."""

from django.test import TestCase

from horilla.testkit import make_company, make_employee, make_user


class TestkitFactorySmokeTests(TestCase):
    def test_make_company_employee_and_user(self):
        company = make_company("Factory Corp")
        user = make_user("factory_user")
        emp = make_employee(
            company=company,
            email="factory@test.horilla",
            first_name="Fac",
            last_name="Tory",
        )
        self.assertEqual(company.company, "Factory Corp")
        self.assertTrue(user.check_password("pass"))
        self.assertEqual(emp.employee_work_info.company_id_id, company.pk)
