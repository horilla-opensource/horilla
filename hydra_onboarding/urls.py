from django.urls import path

from hydra_onboarding import views


urlpatterns = [
    path("", views.onboarding_dashboard, name="hydra-onboarding-dashboard"),
    path("courses/create/", views.course_create, name="hydra-onboarding-course-create"),
    path("courses/<uuid:course_uuid>/", views.course_detail, name="hydra-onboarding-course-detail"),
    path(
        "courses/<uuid:course_uuid>/versions/create/",
        views.version_create,
        name="hydra-onboarding-version-create",
    ),
    path(
        "versions/<uuid:version_uuid>/",
        views.version_detail,
        name="hydra-onboarding-version-detail",
    ),
    path(
        "versions/<uuid:version_uuid>/lessons/create/",
        views.lesson_create,
        name="hydra-onboarding-lesson-create",
    ),
    path(
        "versions/<uuid:version_uuid>/quiz/create/",
        views.quiz_create,
        name="hydra-onboarding-quiz-create",
    ),
    path(
        "versions/<uuid:version_uuid>/publish/",
        views.version_publish,
        name="hydra-onboarding-version-publish",
    ),
    path(
        "quizzes/<uuid:quiz_uuid>/questions/create/",
        views.question_create,
        name="hydra-onboarding-question-create",
    ),
    path(
        "questions/<uuid:question_uuid>/options/create/",
        views.option_create,
        name="hydra-onboarding-option-create",
    ),
    path("rules/create/", views.rule_create, name="hydra-onboarding-rule-create"),
    path(
        "people/<uuid:person_uuid>/assign/",
        views.person_course_assign,
        name="hydra-onboarding-person-assign",
    ),
    path(
        "people/<uuid:person_uuid>/apply-rules/",
        views.person_apply_rules,
        name="hydra-onboarding-person-apply-rules",
    ),
    path(
        "assignments/<uuid:assignment_uuid>/",
        views.assignment_detail,
        name="hydra-onboarding-assignment-detail",
    ),
    path(
        "assignments/<uuid:assignment_uuid>/start/",
        views.assignment_start,
        name="hydra-onboarding-assignment-start",
    ),
    path(
        "assignments/<uuid:assignment_uuid>/quiz/",
        views.assignment_quiz,
        name="hydra-onboarding-assignment-quiz",
    ),
    path(
        "assignments/<uuid:assignment_uuid>/confirm/",
        views.assignment_confirm,
        name="hydra-onboarding-assignment-confirm",
    ),
]
