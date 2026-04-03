"""
Tests for helpdesk module models.

Covers TicketType, DepartmentManager, Ticket, Comment, ClaimRequest,
FAQCategory, and FAQ with CRUD, validation, and field constraint tests.
"""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from helpdesk.models import (
    FAQ,
    MANAGER_TYPES,
    PRIORITY,
    TICKET_STATUS,
    TICKET_TYPES,
    ClaimRequest,
    Comment,
    DepartmentManager,
    FAQCategory,
    Ticket,
    TicketType,
)
from helpdesk.tests.factories import (
    ClaimRequestFactory,
    CommentFactory,
    DepartmentManagerFactory,
    FAQCategoryFactory,
    FAQFactory,
    TicketFactory,
    TicketTypeFactory,
)
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# TicketType Tests
# ---------------------------------------------------------------------------
class TicketTypeTests(HorillaTestCase):
    """CRUD and field tests for TicketType."""

    def test_create_ticket_type(self):
        tt = TicketTypeFactory(title="IT Support", prefix="ITS")
        self.assertIsNotNone(tt.pk)
        self.assertEqual(tt.title, "IT Support")
        self.assertEqual(tt.prefix, "ITS")

    def test_str_representation(self):
        tt = TicketTypeFactory(title="HR Inquiry", prefix="HRI")
        self.assertEqual(str(tt), "HR Inquiry")

    def test_title_unique(self):
        TicketTypeFactory(title="Unique Title", prefix="UT1")
        with self.assertRaises(IntegrityError):
            TicketTypeFactory(title="Unique Title", prefix="UT2")

    def test_prefix_unique(self):
        TicketTypeFactory(title="Type A", prefix="TPA")
        with self.assertRaises(IntegrityError):
            TicketTypeFactory(title="Type B", prefix="TPA")

    def test_type_choices_valid(self):
        """All TICKET_TYPES choice keys are accepted."""
        valid_types = [choice[0] for choice in TICKET_TYPES]
        self.assertIn("suggestion", valid_types)
        self.assertIn("complaint", valid_types)
        self.assertIn("service_request", valid_types)
        self.assertIn("meeting_request", valid_types)
        self.assertIn("anounymous_complaint", valid_types)
        self.assertIn("others", valid_types)

    def test_update_ticket_type(self):
        tt = TicketTypeFactory(title="Old Name", prefix="OLD")
        tt.title = "New Name"
        tt.save()
        tt.refresh_from_db()
        self.assertEqual(tt.title, "New Name")

    def test_delete_ticket_type(self):
        tt = TicketTypeFactory()
        pk = tt.pk
        tt.delete()
        self.assertFalse(TicketType.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# DepartmentManager Tests
# ---------------------------------------------------------------------------
class DepartmentManagerTests(HorillaTestCase):
    """CRUD and validation tests for DepartmentManager."""

    def test_create_department_manager(self):
        dm = DepartmentManager.objects.create(
            manager=self.admin_employee,
            department=self.department,
        )
        self.assertIsNotNone(dm.pk)

    def test_unique_together_department_manager(self):
        """Same (department, manager) pair cannot exist twice."""
        DepartmentManager.objects.create(
            manager=self.admin_employee,
            department=self.department,
        )
        with self.assertRaises(IntegrityError):
            DepartmentManager.objects.create(
                manager=self.admin_employee,
                department=self.department,
            )


# ---------------------------------------------------------------------------
# Ticket Tests
# ---------------------------------------------------------------------------
class TicketTests(HorillaTestCase):
    """CRUD, status transitions, and field tests for Ticket."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ticket_type = TicketTypeFactory(title="General", prefix="GEN")

    def _make_ticket(self, **kwargs):
        defaults = {
            "title": "Test Ticket",
            "employee_id": self.admin_employee,
            "ticket_type": self.ticket_type,
            "description": "A test ticket description",
            "priority": "low",
            "assigning_type": "individual",
            "raised_on": str(self.manager_employee.pk),
            "status": "new",
            "deadline": date.today() + timedelta(days=7),
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)

    def test_create_ticket(self):
        ticket = self._make_ticket()
        self.assertIsNotNone(ticket.pk)
        self.assertEqual(ticket.status, "new")

    def test_str_representation(self):
        ticket = self._make_ticket(title="My Ticket")
        self.assertEqual(str(ticket), "My Ticket")

    def test_status_choices_complete(self):
        """All expected status values are in TICKET_STATUS."""
        valid_statuses = [choice[0] for choice in TICKET_STATUS]
        self.assertIn("new", valid_statuses)
        self.assertIn("in_progress", valid_statuses)
        self.assertIn("on_hold", valid_statuses)
        self.assertIn("resolved", valid_statuses)
        self.assertIn("canceled", valid_statuses)

    def test_priority_choices_complete(self):
        valid_priorities = [choice[0] for choice in PRIORITY]
        self.assertIn("low", valid_priorities)
        self.assertIn("medium", valid_priorities)
        self.assertIn("high", valid_priorities)

    def test_priority_default_is_low(self):
        ticket = self._make_ticket()
        self.assertEqual(ticket.priority, "low")

    def test_status_default_is_new(self):
        ticket = self._make_ticket()
        self.assertEqual(ticket.status, "new")

    def test_employee_fk(self):
        ticket = self._make_ticket()
        self.assertEqual(ticket.employee_id, self.admin_employee)

    def test_assigned_to_m2m(self):
        ticket = self._make_ticket()
        ticket.assigned_to.add(self.manager_employee, self.regular_employee)
        self.assertEqual(ticket.assigned_to.count(), 2)
        self.assertIn(self.manager_employee, ticket.assigned_to.all())

    def test_created_date_auto_set(self):
        ticket = self._make_ticket()
        self.assertEqual(ticket.created_date, date.today())

    def test_deadline_field(self):
        deadline = date.today() + timedelta(days=14)
        ticket = self._make_ticket(deadline=deadline)
        self.assertEqual(ticket.deadline, deadline)

    def test_resolved_date_nullable(self):
        ticket = self._make_ticket()
        self.assertIsNone(ticket.resolved_date)

    def test_resolved_date_can_be_set(self):
        ticket = self._make_ticket()
        ticket.resolved_date = date.today()
        ticket.status = "resolved"
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.resolved_date, date.today())

    def test_status_transition_to_in_progress(self):
        ticket = self._make_ticket()
        ticket.status = "in_progress"
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "in_progress")

    def test_status_transition_to_on_hold(self):
        ticket = self._make_ticket()
        ticket.status = "on_hold"
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "on_hold")

    def test_status_transition_to_resolved(self):
        ticket = self._make_ticket()
        ticket.status = "resolved"
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "resolved")

    def test_status_transition_to_canceled(self):
        ticket = self._make_ticket()
        ticket.status = "canceled"
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "canceled")

    def test_ticket_type_fk(self):
        ticket = self._make_ticket()
        self.assertEqual(ticket.ticket_type, self.ticket_type)

    def test_assigning_type_choices(self):
        valid_types = [choice[0] for choice in MANAGER_TYPES]
        self.assertIn("department", valid_types)
        self.assertIn("job_position", valid_types)
        self.assertIn("individual", valid_types)

    def test_delete_ticket(self):
        ticket = self._make_ticket()
        pk = ticket.pk
        ticket.delete()
        self.assertFalse(Ticket.objects.filter(pk=pk).exists())

    def test_ordering_by_created_date_desc(self):
        """Tickets are ordered by -created_date (Meta.ordering)."""
        t1 = self._make_ticket(title="First")
        t2 = self._make_ticket(title="Second")
        # Meta.ordering is ["-created_date"]. Both tickets share the same
        # created_date (DateField auto_now_add), so just verify the ordering
        # field is declared correctly and both tickets appear.
        self.assertEqual(Ticket._meta.ordering, ["-created_date"])
        tickets = list(Ticket.objects.all())
        self.assertEqual(len(tickets), 2)
        self.assertEqual({tickets[0].pk, tickets[1].pk}, {t1.pk, t2.pk})

    def test_row_colors_new(self):
        ticket = self._make_ticket(status="new")
        self.assertEqual(ticket.row_colors(), "row-status--blue")

    def test_row_colors_in_progress(self):
        ticket = self._make_ticket(status="in_progress")
        self.assertEqual(ticket.row_colors(), "row-status--orange")

    def test_row_colors_on_hold(self):
        ticket = self._make_ticket(status="on_hold")
        self.assertEqual(ticket.row_colors(), "row-status--red")

    def test_row_colors_resolved(self):
        ticket = self._make_ticket(status="resolved")
        self.assertEqual(ticket.row_colors(), "row-status--yellowgreen")

    def test_row_colors_canceled(self):
        ticket = self._make_ticket(status="canceled")
        self.assertEqual(ticket.row_colors(), "row-status--gray")


# ---------------------------------------------------------------------------
# Comment Tests
# ---------------------------------------------------------------------------
class CommentTests(HorillaTestCase):
    """CRUD tests for Comment."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ticket_type = TicketTypeFactory(title="Support", prefix="SUP")

    def _make_ticket(self):
        return Ticket.objects.create(
            title="Comment Test Ticket",
            employee_id=self.admin_employee,
            ticket_type=self.ticket_type,
            description="For comment testing",
            priority="medium",
            assigning_type="individual",
            raised_on=str(self.manager_employee.pk),
            status="new",
            deadline=date.today() + timedelta(days=5),
        )

    def test_create_comment(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="This is a test comment",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        self.assertIsNotNone(comment.pk)
        self.assertEqual(comment.comment, "This is a test comment")

    def test_str_representation(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="Hello world",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        self.assertEqual(str(comment), "Hello world")

    def test_comment_ticket_fk(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="FK test",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        self.assertEqual(comment.ticket, ticket)

    def test_comment_employee_fk(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="Employee FK test",
            ticket=ticket,
            employee_id=self.regular_employee,
        )
        self.assertEqual(comment.employee_id, self.regular_employee)

    def test_comment_date_auto_set(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="Date test",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        self.assertIsNotNone(comment.date)

    def test_delete_comment(self):
        ticket = self._make_ticket()
        comment = Comment.objects.create(
            comment="To delete",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        pk = comment.pk
        comment.delete()
        self.assertFalse(Comment.objects.filter(pk=pk).exists())

    def test_cascade_delete_with_ticket(self):
        """Deleting a ticket cascades to its comments."""
        ticket = self._make_ticket()
        Comment.objects.create(
            comment="Cascade test",
            ticket=ticket,
            employee_id=self.admin_employee,
        )
        ticket_pk = ticket.pk
        ticket.delete()
        self.assertFalse(Comment.objects.filter(ticket__pk=ticket_pk).exists())


# ---------------------------------------------------------------------------
# ClaimRequest Tests
# ---------------------------------------------------------------------------
class ClaimRequestTests(HorillaTestCase):
    """CRUD and validation tests for ClaimRequest."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ticket_type = TicketTypeFactory(title="Claim TT", prefix="CLM")

    def _make_ticket(self):
        return Ticket.objects.create(
            title="Claim Ticket",
            employee_id=self.admin_employee,
            ticket_type=self.ticket_type,
            description="For claim testing",
            priority="high",
            assigning_type="individual",
            raised_on=str(self.manager_employee.pk),
            status="new",
            deadline=date.today() + timedelta(days=3),
        )

    def test_create_claim_request(self):
        ticket = self._make_ticket()
        cr = ClaimRequest.objects.create(
            ticket_id=ticket,
            employee_id=self.regular_employee,
        )
        self.assertIsNotNone(cr.pk)
        self.assertFalse(cr.is_approved)
        self.assertFalse(cr.is_rejected)

    def test_str_representation(self):
        ticket = self._make_ticket()
        cr = ClaimRequest.objects.create(
            ticket_id=ticket,
            employee_id=self.regular_employee,
        )
        result = str(cr)
        self.assertIn(str(ticket), result)
        self.assertIn(str(self.regular_employee), result)

    def test_unique_together_ticket_employee(self):
        ticket = self._make_ticket()
        ClaimRequest.objects.create(
            ticket_id=ticket,
            employee_id=self.regular_employee,
        )
        with self.assertRaises(IntegrityError):
            ClaimRequest.objects.create(
                ticket_id=ticket,
                employee_id=self.regular_employee,
            )

    def test_clean_requires_ticket_id(self):
        cr = ClaimRequest(
            ticket_id=None,
            employee_id=self.regular_employee,
        )
        with self.assertRaises(ValidationError):
            cr.clean()

    def test_clean_requires_employee_id(self):
        ticket = self._make_ticket()
        cr = ClaimRequest(
            ticket_id=ticket,
            employee_id=None,
        )
        with self.assertRaises(ValidationError):
            cr.clean()


# ---------------------------------------------------------------------------
# FAQCategory Tests
# ---------------------------------------------------------------------------
class FAQCategoryTests(HorillaTestCase):
    """CRUD tests for FAQCategory."""

    def test_create_faq_category(self):
        cat = FAQCategoryFactory(title="General")
        self.assertIsNotNone(cat.pk)
        self.assertEqual(cat.title, "General")

    def test_str_representation(self):
        cat = FAQCategoryFactory(title="Payroll FAQ")
        self.assertEqual(str(cat), "Payroll FAQ")

    def test_description_optional(self):
        cat = FAQCategory.objects.create(title="No Description")
        self.assertIsNotNone(cat.pk)
        self.assertIsNone(cat.description)

    def test_update_faq_category(self):
        cat = FAQCategoryFactory(title="Old Category")
        cat.title = "Updated Category"
        cat.save()
        cat.refresh_from_db()
        self.assertEqual(cat.title, "Updated Category")

    def test_delete_faq_category(self):
        cat = FAQCategoryFactory()
        pk = cat.pk
        cat.delete()
        self.assertFalse(FAQCategory.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# FAQ Tests
# ---------------------------------------------------------------------------
class FAQTests(HorillaTestCase):
    """CRUD tests for FAQ."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.faq_category = FAQCategoryFactory(title="HR Questions")

    def test_create_faq(self):
        faq = FAQ.objects.create(
            question="How do I apply for leave?",
            answer="Go to the Leave module and click Apply.",
            category=self.faq_category,
        )
        self.assertIsNotNone(faq.pk)

    def test_str_representation(self):
        faq = FAQ.objects.create(
            question="What is my employee ID?",
            answer="Check your profile page.",
            category=self.faq_category,
        )
        self.assertEqual(str(faq), "What is my employee ID?")

    def test_question_and_answer_fields(self):
        faq = FAQ.objects.create(
            question="Q test",
            answer="A test",
            category=self.faq_category,
        )
        self.assertEqual(faq.question, "Q test")
        self.assertEqual(faq.answer, "A test")

    def test_category_fk(self):
        faq = FAQ.objects.create(
            question="Category FK test",
            answer="Testing FK",
            category=self.faq_category,
        )
        self.assertEqual(faq.category, self.faq_category)

    def test_category_protect_on_delete(self):
        """Deleting a category with FAQs should raise ProtectedError."""
        from django.db.models import ProtectedError

        FAQ.objects.create(
            question="Protected test",
            answer="Should block delete",
            category=self.faq_category,
        )
        with self.assertRaises(ProtectedError):
            self.faq_category.delete()

    def test_tags_m2m(self):
        from base.models import Tags

        tag = Tags.objects.create(title="payroll", color="#ff0000")
        faq = FAQ.objects.create(
            question="Tags test",
            answer="Testing tags",
            category=self.faq_category,
        )
        faq.tags.add(tag)
        self.assertEqual(faq.tags.count(), 1)
        self.assertIn(tag, faq.tags.all())

    def test_delete_faq(self):
        faq = FAQ.objects.create(
            question="To delete",
            answer="Will be deleted",
            category=self.faq_category,
        )
        pk = faq.pk
        faq.delete()
        self.assertFalse(FAQ.objects.filter(pk=pk).exists())

    def test_update_faq(self):
        faq = FAQ.objects.create(
            question="Original question",
            answer="Original answer",
            category=self.faq_category,
        )
        faq.question = "Updated question"
        faq.answer = "Updated answer"
        faq.save()
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Updated question")
        self.assertEqual(faq.answer, "Updated answer")
