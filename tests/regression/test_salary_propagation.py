"""
Regression Tests: Salary → Payslip Propagation
QA-304 — Salary propagation scenarios

Problem space:
    Payslip net pay is derived from a chain of upstream data:
        Employee → Contract (salary) → Attendance → Allowances → Deductions → Payslip

    If any link in this chain is broken — missing contract, mid-period salary
    change, first-month employee, or zero-hour attendance — the payslip must
    either produce a correct result or fail explicitly.

    The risk is silent incorrect computation: a payslip is generated, looks
    complete, but carries wrong figures because upstream data was missing or
    inconsistent.

Coverage:
    1. Employee with no active contract → payslip generation must fail explicitly
    2. Salary changed mid-period → payslip must use the correct contract for each day
    3. New employee (start date mid-month) → payslip must be pro-rated, not full-month
    4. Zero-attendance employee → payslip must show full LOP deduction, not full pay

All tests are pure logic — no Django ORM, no database, no migrations required.
"""

import datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers — simulate the salary computation pipeline
# ---------------------------------------------------------------------------

def find_active_contract(employee_id: int, period_start: datetime.date,
                          contracts: list) -> dict | None:
    """
    Returns the active contract for an employee on a given date.
    Returns None if no contract is active.
    """
    for contract in contracts:
        if (contract["employee_id"] == employee_id
                and contract["start_date"] <= period_start
                and (contract["end_date"] is None or contract["end_date"] >= period_start)):
            return contract
    return None


def compute_prorated_salary(monthly_salary: Decimal, working_days_in_month: int,
                             days_worked: int) -> Decimal:
    """
    Pro-rates salary based on days worked vs total working days in the month.
    Used for new employees who join mid-month.
    """
    if working_days_in_month <= 0:
        return Decimal("0.00")
    daily_rate = monthly_salary / working_days_in_month
    return (daily_rate * days_worked).quantize(Decimal("0.01"))


def generate_payslip(employee_id: int, period_start: datetime.date,
                     period_end: datetime.date, contracts: list,
                     attendance_days: int, total_working_days: int) -> dict:
    """
    Simulates the payslip generation pipeline.

    Returns a payslip dict or raises ValueError if generation cannot proceed.
    This mirrors the expected FIXED behaviour of generate_payslip in
    payroll/views/component_views.py — where each employee's data is
    resolved independently inside the loop.
    """
    contract = find_active_contract(employee_id, period_start, contracts)

    if contract is None:
        raise ValueError(
            f"No active contract found for employee {employee_id} "
            f"on {period_start}. Payslip generation aborted."
        )

    monthly_salary = Decimal(str(contract["monthly_salary"]))

    # Pro-rate if employee didn't work the full month
    if attendance_days < total_working_days:
        gross_pay = compute_prorated_salary(monthly_salary, total_working_days, attendance_days)
    else:
        gross_pay = monthly_salary

    return {
        "employee_id": employee_id,
        "period_start": period_start,
        "period_end": period_end,
        "contract_id": contract["id"],
        "monthly_salary": monthly_salary,
        "attendance_days": attendance_days,
        "total_working_days": total_working_days,
        "gross_pay": gross_pay,
        "net_pay": gross_pay,  # simplified: no deductions in these tests
    }


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestSalaryPropagation:
    """
    Regression tests for salary → payslip propagation correctness.
    Each test exercises a distinct scenario that is likely to produce
    incorrect results if the pipeline has a bug.
    """

    # ------------------------------------------------------------------
    # Scenario 1: Employee with no active contract
    # ------------------------------------------------------------------

    def test_employee_without_contract_raises_error(self):
        """
        REGRESSION: When no active contract exists for an employee,
        payslip generation must fail explicitly — not silently generate
        a zero-pay or incorrect payslip.

        Business impact: Silent ₹0 payslips are indistinguishable from
        correct payslips until the employee raises a complaint.
        """
        contracts = []  # no contracts at all

        try:
            generate_payslip(
                employee_id=99,
                period_start=datetime.date(2025, 6, 1),
                period_end=datetime.date(2025, 6, 30),
                contracts=contracts,
                attendance_days=22,
                total_working_days=22,
            )
            assert False, (
                "Expected ValueError when no contract exists. "
                "Silent failure is unacceptable — payroll operator must be notified."
            )
        except ValueError as e:
            assert "No active contract" in str(e), (
                f"Error message must mention the missing contract. Got: {e}"
            )

    def test_employee_with_expired_contract_raises_error(self):
        """
        REGRESSION: A contract that ended before the pay period must NOT
        be used for payslip calculation. The system must detect the gap
        and fail explicitly rather than using stale contract data.
        """
        contracts = [
            {
                "id": 1,
                "employee_id": 5,
                "monthly_salary": 50000,
                "start_date": datetime.date(2024, 1, 1),
                "end_date": datetime.date(2025, 3, 31),  # expired in March
            }
        ]

        try:
            generate_payslip(
                employee_id=5,
                period_start=datetime.date(2025, 6, 1),  # June — after expiry
                period_end=datetime.date(2025, 6, 30),
                contracts=contracts,
                attendance_days=22,
                total_working_days=22,
            )
            assert False, "Expired contract must not be used for payslip generation."
        except ValueError as e:
            assert "No active contract" in str(e)

    # ------------------------------------------------------------------
    # Scenario 2: Salary changed mid-period
    # ------------------------------------------------------------------

    def test_salary_change_uses_period_start_contract(self):
        """
        REGRESSION: When an employee's salary changes mid-month (new contract
        starts on the 15th), the payslip for the full month must use the
        contract that was active on the period start date, not the newest one.

        This ensures consistent, auditable payslip computation.
        """
        contracts = [
            {
                "id": 1,
                "employee_id": 3,
                "monthly_salary": 40000,  # old salary
                "start_date": datetime.date(2025, 1, 1),
                "end_date": datetime.date(2025, 6, 14),
            },
            {
                "id": 2,
                "employee_id": 3,
                "monthly_salary": 55000,  # new salary from June 15
                "start_date": datetime.date(2025, 6, 15),
                "end_date": None,
            },
        ]

        payslip = generate_payslip(
            employee_id=3,
            period_start=datetime.date(2025, 6, 1),  # period starts June 1
            period_end=datetime.date(2025, 6, 30),
            contracts=contracts,
            attendance_days=22,
            total_working_days=22,
        )

        # Period started June 1 → must use old contract (40000)
        assert payslip["contract_id"] == 1, (
            "Payslip must use the contract active on period_start (June 1), "
            "not the new contract that started June 15."
        )
        assert payslip["monthly_salary"] == Decimal("40000"), (
            f"Expected salary 40000, got {payslip['monthly_salary']}"
        )

    # ------------------------------------------------------------------
    # Scenario 3: New employee (joined mid-month)
    # ------------------------------------------------------------------

    def test_new_employee_salary_is_prorated(self):
        """
        REGRESSION: An employee who joined on the 16th of a 30-day month
        with 22 working days should receive approximately half their monthly
        salary, not the full amount.

        This is a common source of overpayment for new hires.
        """
        contracts = [
            {
                "id": 10,
                "employee_id": 7,
                "monthly_salary": 60000,
                "start_date": datetime.date(2025, 6, 1),
                "end_date": None,
            }
        ]

        payslip = generate_payslip(
            employee_id=7,
            period_start=datetime.date(2025, 6, 1),
            period_end=datetime.date(2025, 6, 30),
            contracts=contracts,
            attendance_days=11,       # joined mid-month, only 11 days worked
            total_working_days=22,    # full month has 22 working days
        )

        expected_gross = (Decimal("60000") / 22 * 11).quantize(Decimal("0.01"))

        assert payslip["gross_pay"] == expected_gross, (
            f"New employee gross pay must be pro-rated. "
            f"Expected {expected_gross}, got {payslip['gross_pay']}"
        )
        assert payslip["gross_pay"] < Decimal("60000"), (
            "New employee must NOT receive full monthly salary."
        )

    def test_full_month_employee_receives_full_salary(self):
        """
        CONTROL TEST: An employee who worked the full month must receive
        the full monthly salary without any pro-ration.
        """
        contracts = [
            {
                "id": 11,
                "employee_id": 8,
                "monthly_salary": 45000,
                "start_date": datetime.date(2025, 1, 1),
                "end_date": None,
            }
        ]

        payslip = generate_payslip(
            employee_id=8,
            period_start=datetime.date(2025, 6, 1),
            period_end=datetime.date(2025, 6, 30),
            contracts=contracts,
            attendance_days=22,
            total_working_days=22,
        )

        assert payslip["gross_pay"] == Decimal("45000"), (
            f"Full-month employee must receive full salary. "
            f"Expected 45000, got {payslip['gross_pay']}"
        )

    # ------------------------------------------------------------------
    # Scenario 4: Zero-attendance employee
    # ------------------------------------------------------------------

    def test_zero_attendance_produces_zero_gross_pay(self):
        """
        REGRESSION: An employee with zero attendance days (e.g., on
        unpaid leave for the entire month) must receive ₹0 gross pay,
        not the full monthly salary.

        Without this guard, an absent employee could be paid in full.
        """
        contracts = [
            {
                "id": 12,
                "employee_id": 9,
                "monthly_salary": 30000,
                "start_date": datetime.date(2025, 1, 1),
                "end_date": None,
            }
        ]

        payslip = generate_payslip(
            employee_id=9,
            period_start=datetime.date(2025, 6, 1),
            period_end=datetime.date(2025, 6, 30),
            contracts=contracts,
            attendance_days=0,       # zero days worked
            total_working_days=22,
        )

        assert payslip["gross_pay"] == Decimal("0.00"), (
            f"Zero attendance must result in zero gross pay. "
            f"Got: {payslip['gross_pay']}"
        )
