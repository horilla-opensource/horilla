from uuid import uuid4

from django import forms
from django.utils.translation import gettext_lazy as _

from base.models import Department, EmployeeType
from hydra_coordination.models import Location, Team
from hydra_coordination.selectors import (
    departments_for_user,
    locations_for_user,
    teams_for_user,
)
from hydra_onboarding.models import (
    Course,
    CourseAssignmentRule,
    CourseVersion,
    Lesson,
    Quiz,
    QuizOption,
    QuizQuestion,
)
from hydra_onboarding.selectors import (
    course_versions_for_user,
    courses_for_user,
    onboarding_companies_for_user,
)


def _style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.RadioSelect):
            continue
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "oh-switch__checkbox"
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs["class"] = "oh-select oh-select-2 w-100"
        else:
            field.widget.attrs["class"] = "oh-input w-100"


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("company", "code", "name", "description", "default_language")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = onboarding_companies_for_user(user=actor)
        _style_fields(self)


class CourseVersionForm(forms.Form):
    language = forms.ChoiceField(
        label=_("Language"),
        choices=CourseVersion._meta.get_field("language").choices,
    )
    title = forms.CharField(label=_("Title"), max_length=180)
    summary = forms.CharField(
        label=_("Summary"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = (
            "sequence",
            "title",
            "body",
            "estimated_minutes",
            "requires_confirmation",
        )
        widgets = {"body": forms.Textarea(attrs={"rows": 10})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title", "passing_score", "max_attempts")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ("sequence", "prompt")
        widgets = {"prompt": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class QuizOptionForm(forms.ModelForm):
    class Meta:
        model = QuizOption
        fields = ("sequence", "label", "is_correct")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class CourseAssignmentRuleForm(forms.ModelForm):
    class Meta:
        model = CourseAssignmentRule
        fields = (
            "company",
            "course",
            "priority",
            "location",
            "department",
            "team",
            "language",
            "employee_type",
            "due_days",
            "is_mandatory",
        )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        company_ids = onboarding_companies_for_user(user=actor).values("pk")
        self.fields["company"].queryset = onboarding_companies_for_user(user=actor)
        self.fields["course"].queryset = courses_for_user(user=actor).filter(
            is_active=True
        )
        self.fields["location"].queryset = locations_for_user(user=actor)
        self.fields["department"].queryset = departments_for_user(user=actor)
        self.fields["team"].queryset = teams_for_user(user=actor)
        self.fields["employee_type"].queryset = EmployeeType._base_manager.filter(
            company_id__in=company_ids
        ).distinct()
        self.fields["language"].required = False
        _style_fields(self)


class ManualCourseAssignmentForm(forms.Form):
    course_version = forms.ModelChoiceField(
        label=_("Published course version"),
        queryset=CourseVersion._base_manager.none(),
    )
    due_at = forms.DateField(
        label=_("Due date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    request_key = forms.UUIDField(widget=forms.HiddenInput())

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_version"].queryset = course_versions_for_user(
            user=actor
        ).filter(status=CourseVersion.Status.PUBLISHED, is_active=True)
        if not self.is_bound:
            self.initial["request_key"] = uuid4()
        _style_fields(self)


class QuizAttemptForm(forms.Form):
    def __init__(self, *args, quiz, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz
        for question in quiz.questions.prefetch_related("options").order_by(
            "sequence", "pk"
        ):
            self.fields[f"question_{question.uuid}"] = forms.ModelChoiceField(
                label=question.prompt,
                queryset=question.options.order_by("sequence", "pk"),
                widget=forms.RadioSelect,
                empty_label=None,
            )

    @property
    def answers(self):
        if not self.is_valid():
            return {}
        return {
            field_name.removeprefix("question_"): str(option.uuid)
            for field_name, option in self.cleaned_data.items()
            if field_name.startswith("question_")
        }


class CourseConfirmationForm(forms.Form):
    acknowledge = forms.BooleanField(
        label=_("I confirm that the assigned course was reviewed and completed."),
    )
    statement = forms.CharField(
        label=_("Confirmation statement"),
        max_length=500,
        initial=_("Assigned onboarding course completed."),
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
