"""
Factory Boy factories for payroll module models.

Provides test factories for all major payroll models:
- PayrollSettings, FilingStatus, TaxBracket
- Contract, Allowance, Deduction
- Payslip, LoanAccount, Reimbursement

Usage:
    contract = ContractFactory(employee_id=my_employee)
    payslip = PayslipFactory(employee_id=my_employee, status="confirmed")
    bracket = TaxBracketFactory(min_income=0, max_income=10000, tax_rate=10)
"""

from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory
from employee.tests.factories import EmployeeFactory
from payroll.models.models import (
    Allowance,
    Contract,
    Deduction,
    FilingStatus,
    LoanAccount,
    Payslip,
    Reimbursement,
)
from payroll.models.tax_models import PayrollSettings, TaxBracket


class PayrollSettingsFactory(DjangoModelFactory):
    class Meta:
        model = PayrollSettings

    currency_symbol = "$"
    position = "postfix"
    company_id = factory.SubFactory(CompanyFactory)


class FilingStatusFactory(DjangoModelFactory):
    class Meta:
        model = FilingStatus

    filing_status = factory.Sequence(lambda n: f"Filing Status {n}")
    based_on = "basic_pay"
    company_id = factory.SubFactory(CompanyFactory)


class TaxBracketFactory(DjangoModelFactory):
    class Meta:
        model = TaxBracket

    filing_status_id = factory.SubFactory(FilingStatusFactory)
    min_income = 0.0
    max_income = 10000.0
    tax_rate = 10.0


class ContractFactory(DjangoModelFactory):
    class Meta:
        model = Contract

    contract_name = factory.Sequence(lambda n: f"Contract {n}")
    employee_id = factory.SubFactory(EmployeeFactory)
    wage = 5000.0
    contract_status = "active"
    wage_type = "monthly"
    pay_frequency = "monthly"
    contract_start_date = factory.LazyFunction(
        lambda: date.today() - timedelta(days=365)
    )
    contract_end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=365))


class AllowanceFactory(DjangoModelFactory):
    class Meta:
        model = Allowance

    title = factory.Sequence(lambda n: f"Allowance {n}")
    is_fixed = True
    amount = 500.0
    is_taxable = True
    include_active_employees = False

    class Params:
        percentage = factory.Trait(
            is_fixed=False,
            amount=None,
            based_on="basic_pay",
            rate=10.0,
        )


class DeductionFactory(DjangoModelFactory):
    class Meta:
        model = Deduction

    title = factory.Sequence(lambda n: f"Deduction {n}")
    is_fixed = True
    amount = 100.0
    is_pretax = True
    include_active_employees = False

    class Params:
        percentage = factory.Trait(
            is_fixed=False,
            amount=None,
            based_on="basic_pay",
            rate=5.0,
        )


class PayslipFactory(DjangoModelFactory):
    class Meta:
        model = Payslip

    employee_id = factory.SubFactory(EmployeeFactory)
    start_date = factory.LazyFunction(lambda: date.today().replace(day=1))
    end_date = factory.LazyFunction(lambda: date.today())
    pay_head_data = factory.LazyFunction(lambda: {"net_pay": 5000, "basic_pay": 4000})
    contract_wage = 5000.0
    basic_pay = 4000.0
    gross_pay = 4500.0
    deduction = 500.0
    net_pay = 4000.0
    status = "draft"


class LoanAccountFactory(DjangoModelFactory):
    class Meta:
        model = LoanAccount

    title = factory.Sequence(lambda n: f"Loan {n}")
    employee_id = factory.SubFactory(EmployeeFactory)
    type = "loan"
    loan_amount = 10000.0
    installments = 12
    provided_date = factory.LazyFunction(date.today)
    installment_start_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=30)
    )


class ReimbursementFactory(DjangoModelFactory):
    class Meta:
        model = Reimbursement

    title = factory.Sequence(lambda n: f"Reimbursement {n}")
    employee_id = factory.SubFactory(EmployeeFactory)
    type = "reimbursement"
    amount = 500.0
    status = "requested"
    allowance_on = factory.LazyFunction(date.today)
    attachment = factory.django.FileField(filename="receipt.pdf")
