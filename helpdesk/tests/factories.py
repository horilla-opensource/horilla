"""
Factory Boy factories for helpdesk module models.

Usage:
    ticket_type = TicketTypeFactory()
    dept_manager = DepartmentManagerFactory(manager=emp, department=dept)
    ticket = TicketFactory(employee_id=emp, ticket_type=ticket_type)
    comment = CommentFactory(ticket=ticket, employee_id=emp)
    faq_category = FAQCategoryFactory()
    faq = FAQFactory(category=faq_category)
"""

from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory, DepartmentFactory
from employee.tests.factories import EmployeeFactory
from helpdesk.models import (
    FAQ,
    Attachment,
    ClaimRequest,
    Comment,
    DepartmentManager,
    FAQCategory,
    Ticket,
    TicketType,
)


class TicketTypeFactory(DjangoModelFactory):
    class Meta:
        model = TicketType

    title = factory.Sequence(lambda n: f"Ticket Type {n}")
    type = "suggestion"
    prefix = factory.Sequence(lambda n: f"T{n:01d}"[:3])


class DepartmentManagerFactory(DjangoModelFactory):
    class Meta:
        model = DepartmentManager

    manager = factory.SubFactory(EmployeeFactory)
    department = factory.SubFactory(DepartmentFactory)


class TicketFactory(DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Sequence(lambda n: f"Ticket {n}")
    employee_id = factory.SubFactory(EmployeeFactory)
    ticket_type = factory.SubFactory(TicketTypeFactory)
    description = factory.Faker("sentence")
    priority = "low"
    assigning_type = "individual"
    raised_on = "1"
    status = "new"
    deadline = factory.LazyFunction(lambda: date.today() + timedelta(days=7))


class ClaimRequestFactory(DjangoModelFactory):
    class Meta:
        model = ClaimRequest

    ticket_id = factory.SubFactory(TicketFactory)
    employee_id = factory.SubFactory(EmployeeFactory)
    is_approved = False
    is_rejected = False


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    comment = factory.Faker("paragraph")
    ticket = factory.SubFactory(TicketFactory)
    employee_id = factory.SubFactory(EmployeeFactory)


class FAQCategoryFactory(DjangoModelFactory):
    class Meta:
        model = FAQCategory

    title = factory.Sequence(lambda n: f"FAQ Category {n}")
    description = factory.Faker("sentence")


class FAQFactory(DjangoModelFactory):
    class Meta:
        model = FAQ

    question = factory.Sequence(lambda n: f"How do I do thing {n}?")
    answer = factory.Faker("paragraph")
    category = factory.SubFactory(FAQCategoryFactory)
