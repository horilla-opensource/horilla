"""
Factory Boy factories for PMS (Performance Management System) module models.

Usage:
    period = PeriodFactory()
    obj = ObjectiveFactory(company_id=my_company)
    kr = KeyResultFactory(company_id=my_company)
    emp_obj = EmployeeObjectiveFactory(employee_id=emp, objective_id=obj)
    emp_kr = EmployeeKeyResultFactory(employee_objective_id=emp_obj, key_result_id=kr)
    feedback = FeedbackFactory(employee_id=emp, manager_id=mgr)
    question = QuestionFactory(template_id=qt)
    answer = AnswerFactory(feedback_id=feedback, question_id=question, employee_id=emp)
    bps = BonusPointSettingFactory()
"""

from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory
from employee.tests.factories import EmployeeFactory
from pms.models import (
    Answer,
    BonusPointSetting,
    Comment,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    Objective,
    Period,
    Question,
    QuestionOptions,
    QuestionTemplate,
)


class PeriodFactory(DjangoModelFactory):
    class Meta:
        model = Period

    period_name = factory.Sequence(lambda n: f"Q{n} 2026")
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=90))

    @factory.post_generation
    def company_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if hasattr(extracted, "__iter__"):
                for company in extracted:
                    self.company_id.add(company)
            else:
                self.company_id.add(extracted)


class KeyResultFactory(DjangoModelFactory):
    class Meta:
        model = KeyResult

    title = factory.Sequence(lambda n: f"Key Result {n}")
    description = factory.Faker("sentence")
    progress_type = "%"
    target_value = 100
    duration = 30
    company_id = factory.SubFactory(CompanyFactory)


class ObjectiveFactory(DjangoModelFactory):
    class Meta:
        model = Objective
        exclude = ["_skip_save_override"]

    _skip_save_override = True

    title = factory.Sequence(lambda n: f"Objective {n}")
    description = factory.Faker("sentence")
    duration = 30
    duration_unit = "days"
    company_id = factory.SubFactory(CompanyFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override _create to bypass Objective.save() which accesses
        _thread_locals.request.session for selected_company.
        We call models.Model.save() directly.
        """
        from django.db import models as dj_models

        kwargs.pop("_skip_save_override", None)
        obj = model_class(*args, **kwargs)
        dj_models.Model.save(obj)
        return obj

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.managers.add(emp)

    @factory.post_generation
    def assignees(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.assignees.add(emp)

    @factory.post_generation
    def key_result_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if hasattr(extracted, "__iter__"):
                for kr in extracted:
                    self.key_result_id.add(kr)
            else:
                self.key_result_id.add(extracted)


class EmployeeObjectiveFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeObjective

    objective = factory.Sequence(lambda n: f"Emp Objective {n}")
    objective_description = factory.Faker("sentence")
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    status = "Not Started"
    employee_id = factory.SubFactory(EmployeeFactory)
    objective_id = factory.SubFactory(ObjectiveFactory)


class EmployeeKeyResultFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeKeyResult

    key_result = factory.Sequence(lambda n: f"Emp KR {n}")
    key_result_description = factory.Faker("sentence")
    employee_objective_id = factory.SubFactory(EmployeeObjectiveFactory)
    key_result_id = factory.SubFactory(KeyResultFactory)
    progress_type = "%"
    status = "Not Started"
    start_value = 0
    current_value = 0
    target_value = 100
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))


class QuestionTemplateFactory(DjangoModelFactory):
    class Meta:
        model = QuestionTemplate

    question_template = factory.Sequence(lambda n: f"Template {n}")

    @factory.post_generation
    def company_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if hasattr(extracted, "__iter__"):
                for company in extracted:
                    self.company_id.add(company)
            else:
                self.company_id.add(extracted)


class QuestionFactory(DjangoModelFactory):
    class Meta:
        model = Question

    question = factory.Sequence(lambda n: f"Question {n}?")
    question_type = "1"  # Text
    template_id = factory.SubFactory(QuestionTemplateFactory)


class QuestionOptionsFactory(DjangoModelFactory):
    class Meta:
        model = QuestionOptions

    question_id = factory.SubFactory(QuestionFactory)
    option_a = "Option A"
    option_b = "Option B"
    option_c = "Option C"
    option_d = "Option D"


class FeedbackFactory(DjangoModelFactory):
    class Meta:
        model = Feedback

    review_cycle = factory.Sequence(lambda n: f"Review Cycle {n}")
    employee_id = factory.SubFactory(EmployeeFactory)
    manager_id = factory.SubFactory(EmployeeFactory)
    question_template_id = factory.SubFactory(QuestionTemplateFactory)
    status = "Not Started"
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))


class AnswerFactory(DjangoModelFactory):
    class Meta:
        model = Answer

    answer = {"text": "Good performance"}
    question_id = factory.SubFactory(QuestionFactory)
    employee_id = factory.SubFactory(EmployeeFactory)
    feedback_id = factory.SubFactory(FeedbackFactory)


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    comment = factory.Faker("paragraph")
    employee_id = factory.SubFactory(EmployeeFactory)
    employee_objective_id = factory.SubFactory(EmployeeObjectiveFactory)


class BonusPointSettingFactory(DjangoModelFactory):
    class Meta:
        model = BonusPointSetting

    model = "pms.models.EmployeeObjective"
    bonus_for = "Closed"
    points = 10
    is_active = True
