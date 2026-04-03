"""
Factory Boy factories for employee module models.

NOTE: Employee.save() auto-creates HorillaUser and EmployeeWorkInformation.
The EmployeeFactory works WITH this cascading creation — do NOT manually
set employee_user_id or create EmployeeWorkInformation separately.

Usage:
    emp = EmployeeFactory()                    # basic employee
    emp = EmployeeFactory(
        work_info__company_id=my_company,      # set work info company
        work_info__department_id=my_dept,       # set work info department
    )
"""

import factory
from factory.django import DjangoModelFactory

from employee.models import Employee, EmployeeBankDetails, EmployeeWorkInformation


class EmployeeFactory(DjangoModelFactory):
    class Meta:
        model = Employee
        skip_postgeneration_save = True

    employee_first_name = factory.Faker("first_name")
    employee_last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"employee.{n}@test.com")
    phone = factory.Sequence(lambda n: f"555{n:07d}")
    gender = "male"

    @factory.post_generation
    def work_info(self, create, extracted, **kwargs):
        """
        Update the auto-created EmployeeWorkInformation with kwargs.
        Employee.save() already created it — we just update fields.
        """
        if not create:
            return
        try:
            work_info = self.employee_work_info
        except EmployeeWorkInformation.DoesNotExist:
            return
        changed = False
        for key, value in kwargs.items():
            setattr(work_info, key, value)
            changed = True
        if changed:
            work_info.save()


class EmployeeBankDetailsFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeBankDetails

    employee_id = factory.SubFactory(EmployeeFactory)
    bank_name = factory.Faker("company")
    account_number = factory.Sequence(lambda n: f"ACC{n:010d}")
    branch = factory.Faker("city")
