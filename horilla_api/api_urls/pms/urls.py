"""
horilla_api/api_urls/pms/urls.py
"""

from django.urls import path

from horilla_api.api_views.pms.views import *

urlpatterns = [
    # Period URLs
    path("period/", PeriodGetCreateAPIView.as_view()),
    path("period/<int:pk>/", PeriodGetUpdateDeleteAPIView.as_view()),
    # KeyResult URLs
    path("key-result/", KeyResultGetCreateAPIView.as_view()),
    path("key-result/<int:pk>/", KeyResultGetUpdateDeleteAPIView.as_view()),
    # Objective URLs
    path("objective/", ObjectiveGetCreateAPIView.as_view()),
    path("objective/<int:pk>/", ObjectiveGetUpdateDeleteAPIView.as_view()),
    # EmployeeObjective URLs
    path("employee-objective/", EmployeeObjectiveGetCreateAPIView.as_view()),
    path(
        "employee-objective/<int:pk>/",
        EmployeeObjectiveGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "employee/<int:employee_id>/employee-objective/",
        EmployeeObjectiveGetCreateAPIView.as_view(),
    ),
    path(
        "objective/<int:objective_id>/employee-objective/",
        EmployeeObjectiveGetCreateAPIView.as_view(),
    ),
    # EmployeeKeyResult URLs
    path("employee-key-result/", EmployeeKeyResultGetCreateAPIView.as_view()),
    path(
        "employee-key-result/<int:pk>/",
        EmployeeKeyResultGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "employee-objective/<int:employee_objective_id>/employee-key-result/",
        EmployeeKeyResultGetCreateAPIView.as_view(),
    ),
    path(
        "key-result/<int:key_result_id>/employee-key-result/",
        EmployeeKeyResultGetCreateAPIView.as_view(),
    ),
    # Comment URLs
    path("comment/", CommentGetCreateAPIView.as_view()),
    path("comment/<int:pk>/", CommentGetUpdateDeleteAPIView.as_view()),
    path(
        "employee-objective/<int:employee_objective_id>/comment/",
        CommentGetCreateAPIView.as_view(),
    ),
    # QuestionTemplate URLs
    path("question-template/", QuestionTemplateGetCreateAPIView.as_view()),
    path(
        "question-template/<int:pk>/", QuestionTemplateGetUpdateDeleteAPIView.as_view()
    ),
    # Question URLs
    path("question/", QuestionGetCreateAPIView.as_view()),
    path("question/<int:pk>/", QuestionGetUpdateDeleteAPIView.as_view()),
    path(
        "question-template/<int:template_id>/question/",
        QuestionGetCreateAPIView.as_view(),
    ),
    # QuestionOptions URLs
    path("question-options/", QuestionOptionsGetCreateAPIView.as_view()),
    path("question-options/<int:pk>/", QuestionOptionsGetUpdateDeleteAPIView.as_view()),
    path(
        "question/<int:question_id>/question-options/",
        QuestionOptionsGetCreateAPIView.as_view(),
    ),
    # Feedback URLs
    path("feedback/", FeedbackGetCreateAPIView.as_view()),
    path("feedback/<int:pk>/", FeedbackGetUpdateDeleteAPIView.as_view()),
    path("employee/<int:employee_id>/feedback/", FeedbackGetCreateAPIView.as_view()),
    # Answer URLs
    path("answer/", AnswerGetCreateAPIView.as_view()),
    path("answer/<int:pk>/", AnswerGetUpdateDeleteAPIView.as_view()),
    path("feedback/<int:feedback_id>/answer/", AnswerGetCreateAPIView.as_view()),
    path("question/<int:question_id>/answer/", AnswerGetCreateAPIView.as_view()),
    # KeyResultFeedback URLs
    path("key-result-feedback/", KeyResultFeedbackGetCreateAPIView.as_view()),
    path(
        "key-result-feedback/<int:pk>/",
        KeyResultFeedbackGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "feedback/<int:feedback_id>/key-result-feedback/",
        KeyResultFeedbackGetCreateAPIView.as_view(),
    ),
    path(
        "employee-key-result/<int:key_result_id>/key-result-feedback/",
        KeyResultFeedbackGetCreateAPIView.as_view(),
    ),
    # Meetings URLs
    path("meetings/", MeetingsGetCreateAPIView.as_view()),
    path("meetings/<int:pk>/", MeetingsGetUpdateDeleteAPIView.as_view()),
    # MeetingsAnswer URLs
    path("meetings-answer/", MeetingsAnswerGetCreateAPIView.as_view()),
    path("meetings-answer/<int:pk>/", MeetingsAnswerGetUpdateDeleteAPIView.as_view()),
    path(
        "meetings/<int:meeting_id>/meetings-answer/",
        MeetingsAnswerGetCreateAPIView.as_view(),
    ),
    path(
        "question/<int:question_id>/meetings-answer/",
        MeetingsAnswerGetCreateAPIView.as_view(),
    ),
    # EmployeeBonusPoint URLs
    path("employee-bonus-point/", EmployeeBonusPointGetCreateAPIView.as_view()),
    path(
        "employee-bonus-point/<int:pk>/",
        EmployeeBonusPointGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "employee/<int:employee_id>/employee-bonus-point/",
        EmployeeBonusPointGetCreateAPIView.as_view(),
    ),
    # BonusPointSetting URLs
    path("bonus-point-setting/", BonusPointSettingGetCreateAPIView.as_view()),
    path(
        "bonus-point-setting/<int:pk>/",
        BonusPointSettingGetUpdateDeleteAPIView.as_view(),
    ),
    # AnonymousFeedback URLs
    path("anonymous-feedback/", AnonymousFeedbackGetCreateAPIView.as_view()),
    path(
        "anonymous-feedback/<int:pk>/",
        AnonymousFeedbackGetUpdateDeleteAPIView.as_view(),
    ),
]
