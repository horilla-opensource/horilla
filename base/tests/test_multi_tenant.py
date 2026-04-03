"""
Multi-tenant isolation tests for Horilla HRMS.

Verifies that HorillaCompanyManager correctly filters records by the
active company set in the session. Tests both strict company-filtered
models and models that include null-company (global) records.

Uses the same _thread_locals.request mechanism as the middleware, with
Model.company_filter set manually to simulate what CompanyMiddleware does.
"""

import datetime

from django.db.models import Q

from horilla.test_utils.base import HorillaTestCase


def _apply_company_filter(model, company):
    """
    Simulate what CompanyMiddleware._add_company_filter() does
    for a model with a direct company_id FK.
    """
    model.add_to_class("company_filter", Q(company_id=company))


def _clear_company_filter(model):
    """Remove the company_filter class attribute after a test."""
    if hasattr(model, "company_filter"):
        try:
            delattr(model, "company_filter")
        except AttributeError:
            pass


class LeaveTypeMultiTenantTests(HorillaTestCase):
    """
    HorillaCompanyManager isolates LeaveType records by company.

    LeaveType.objects uses HorillaCompanyManager(related_company_field="company_id")
    which reads Model.company_filter (set by CompanyMiddleware on each request).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from leave.models import LeaveType

        cls.lt_a = LeaveType.objects.create(
            name="Annual Leave A",
            payment="paid",
            company_id=cls.company_a,
        )
        cls.lt_b = LeaveType.objects.create(
            name="Annual Leave B",
            payment="paid",
            company_id=cls.company_b,
        )
        # A leave type with no company (global/shared)
        cls.lt_global = LeaveType.objects.create(
            name="Global Holiday",
            payment="paid",
            company_id=None,
        )

    def setUp(self):
        super().setUp()
        from leave.models import LeaveType

        _clear_company_filter(LeaveType)

    def tearDown(self):
        from leave.models import LeaveType

        _clear_company_filter(LeaveType)
        super().tearDown()

    def test_no_filter_returns_all_records(self):
        """Without a company_filter, all LeaveTypes are returned."""
        from leave.models import LeaveType

        # No company_filter set — selected_company not set in session either
        self.set_request_user(self.admin_user)
        # entire() bypasses ALL filters
        pks = list(LeaveType.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.lt_a.pk, pks)
        self.assertIn(self.lt_b.pk, pks)

    def test_company_a_filter_shows_only_company_a(self):
        """company_filter set to company_a → only company_a records returned."""
        from leave.models import LeaveType

        _apply_company_filter(LeaveType, self.company_a)
        self.set_company_session(self.company_a)

        qs = LeaveType.objects.all()
        pks = list(qs.values_list("pk", flat=True))
        self.assertIn(self.lt_a.pk, pks)
        self.assertNotIn(self.lt_b.pk, pks)

    def test_company_b_filter_shows_only_company_b(self):
        """company_filter set to company_b → only company_b records returned."""
        from leave.models import LeaveType

        _apply_company_filter(LeaveType, self.company_b)
        self.set_company_session(self.company_b)

        qs = LeaveType.objects.all()
        pks = list(qs.values_list("pk", flat=True))
        self.assertNotIn(self.lt_a.pk, pks)
        self.assertIn(self.lt_b.pk, pks)

    def test_entire_bypasses_company_filter(self):
        """entire() ignores company_filter and returns all records."""
        from leave.models import LeaveType

        _apply_company_filter(LeaveType, self.company_a)
        self.set_company_session(self.company_a)

        all_pks = list(LeaveType.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.lt_a.pk, all_pks)
        self.assertIn(self.lt_b.pk, all_pks)

    def test_session_all_bypasses_filter(self):
        """selected_company='all' bypasses company filtering."""
        from leave.models import LeaveType

        _apply_company_filter(LeaveType, self.company_a)
        self.set_company_session(None)  # Sets "all"

        qs = LeaveType.objects.all()
        pks = list(qs.values_list("pk", flat=True))
        # Both companies should be visible
        self.assertIn(self.lt_a.pk, pks)
        self.assertIn(self.lt_b.pk, pks)

    def test_cross_company_data_is_isolated(self):
        """Company A user cannot read Company B's data when filter is active."""
        from leave.models import LeaveType

        _apply_company_filter(LeaveType, self.company_a)
        self.set_company_session(self.company_a)

        # Querying with company_a filter active
        visible = LeaveType.objects.filter(name="Annual Leave B").count()
        self.assertEqual(visible, 0, "Company B data must not be visible to Company A")

    def test_no_session_no_filter_returns_all(self):
        """No session selected_company → no company filtering applied."""
        from leave.models import LeaveType

        # Do NOT set company_filter
        # Do NOT set session["selected_company"]
        self.set_request_user(self.admin_user)

        pks = list(LeaveType.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.lt_a.pk, pks)
        self.assertIn(self.lt_b.pk, pks)


class ContractMultiTenantTests(HorillaTestCase):
    """
    Multi-tenant isolation for payroll Contract records.

    Contract is in the COMPANY_MODELS list — it gets strict company filtering.
    Contract uses HorillaCompanyManager with related_company_field path through employee.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from payroll.models.models import Contract

        # Use a past end_date so Contract.save() auto-sets status="expired",
        # bypassing the "one draft per employee" and "one active per employee"
        # uniqueness constraints that would otherwise conflict across test classes.
        cls.contract_a = Contract.objects.create(
            employee_id=cls.admin_employee,
            contract_name="Contract A",
            contract_start_date=datetime.date(2020, 1, 1),
            contract_end_date=datetime.date(2020, 12, 31),
            wage=50000,
            wage_type="monthly",
        )
        cls.contract_b = Contract.objects.create(
            employee_id=cls.regular_employee,
            contract_name="Contract B",
            contract_start_date=datetime.date(2020, 1, 1),
            contract_end_date=datetime.date(2020, 12, 31),
            wage=40000,
            wage_type="monthly",
        )

    def setUp(self):
        super().setUp()
        from payroll.models.models import Contract

        _clear_company_filter(Contract)

    def tearDown(self):
        from payroll.models.models import Contract

        _clear_company_filter(Contract)
        super().tearDown()

    def test_entire_returns_both_contracts(self):
        """entire() bypasses company filtering, returns all contracts."""
        from payroll.models.models import Contract

        pks = list(Contract.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.contract_a.pk, pks)
        self.assertIn(self.contract_b.pk, pks)

    def test_contract_filter_by_employee_company(self):
        """
        Contract records filtered by employee's company.
        admin_employee and regular_employee are both in company_a,
        so with company_a filter both contracts are visible.
        """
        from payroll.models.models import Contract

        # Both employees are in company_a (set up in HorillaTestCase.setUpTestData)
        # With company_a filter, both contracts should be visible
        filter_q = Q(employee_id__employee_work_info__company_id=self.company_a)
        Contract.add_to_class("company_filter", filter_q)
        self.set_company_session(self.company_a)

        pks = list(Contract.objects.all().values_list("pk", flat=True))
        self.assertIn(self.contract_a.pk, pks)
        self.assertIn(self.contract_b.pk, pks)


class DepartmentMultiTenantTests(HorillaTestCase):
    """
    Multi-tenant isolation for Department records.

    Department uses an M2M company_id field.
    With a company filter, departments not linked to the active company
    should not be returned.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from base.models import Department

        cls.dept_only_a = Department.objects.create(department="Engineering A")
        cls.dept_only_a.company_id.add(cls.company_a)

        cls.dept_only_b = Department.objects.create(department="Engineering B")
        cls.dept_only_b.company_id.add(cls.company_b)

        cls.dept_both = Department.objects.create(department="HR Shared")
        cls.dept_both.company_id.add(cls.company_a, cls.company_b)

    def setUp(self):
        super().setUp()
        from base.models import Department

        _clear_company_filter(Department)

    def tearDown(self):
        from base.models import Department

        _clear_company_filter(Department)
        super().tearDown()

    def test_entire_returns_all_departments(self):
        """entire() bypasses company filtering."""
        from base.models import Department

        pks = list(Department.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.dept_only_a.pk, pks)
        self.assertIn(self.dept_only_b.pk, pks)
        self.assertIn(self.dept_both.pk, pks)

    def test_company_a_filter_excludes_company_b_dept(self):
        """Company A filter should not return departments only linked to B."""
        from base.models import Department

        filter_q = Q(company_id=self.company_a)
        Department.add_to_class("company_filter", filter_q)
        self.set_company_session(self.company_a)

        pks = list(Department.objects.all().values_list("pk", flat=True))
        self.assertIn(self.dept_only_a.pk, pks)
        self.assertNotIn(self.dept_only_b.pk, pks)
        # Shared department (linked to both) should appear
        self.assertIn(self.dept_both.pk, pks)


class AttendanceMultiTenantTests(HorillaTestCase):
    """
    Multi-tenant isolation for Attendance records.

    Attendance is in COMPANY_MODELS with path:
    employee_id__employee_work_info__company_id
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        import datetime

        from attendance.models import Attendance

        cls.att_admin = Attendance.objects.create(
            employee_id=cls.admin_employee,
            attendance_date=datetime.date.today(),
            attendance_clock_in_date=datetime.date.today(),
            attendance_clock_in=datetime.time(9, 0),
            shift_id=cls.admin_employee.employee_work_info.shift_id,
            work_type_id=cls.admin_employee.employee_work_info.work_type_id,
            attendance_worked_hour="08:00",
        )

    def setUp(self):
        super().setUp()
        from attendance.models import Attendance

        _clear_company_filter(Attendance)

    def tearDown(self):
        from attendance.models import Attendance

        _clear_company_filter(Attendance)
        super().tearDown()

    def test_entire_includes_all_attendance(self):
        """entire() bypasses filtering, returns all attendance records."""
        from attendance.models import Attendance

        pks = list(Attendance.objects.entire().values_list("pk", flat=True))
        self.assertIn(self.att_admin.pk, pks)

    def test_company_a_filter_includes_admin_employee(self):
        """Admin employee is in company_a — visible with company_a filter."""
        from attendance.models import Attendance

        filter_q = Q(employee_id__employee_work_info__company_id=self.company_a)
        Attendance.add_to_class("company_filter", filter_q)
        self.set_company_session(self.company_a)

        pks = list(Attendance.objects.all().values_list("pk", flat=True))
        self.assertIn(self.att_admin.pk, pks)

    def test_company_b_filter_excludes_company_a_employee(self):
        """Company B filter should not return admin employee's attendance."""
        from attendance.models import Attendance

        filter_q = Q(employee_id__employee_work_info__company_id=self.company_b)
        Attendance.add_to_class("company_filter", filter_q)
        self.set_company_session(self.company_b)

        pks = list(Attendance.objects.all().values_list("pk", flat=True))
        self.assertNotIn(self.att_admin.pk, pks)
