"""
horilla_api/urls/attendance/urls.py
"""

from django.urls import path
from horilla_api.api_views.attendance.views import *
from horilla_api.api_views.attendance.permission_views import AttendancePermissionCheck

urlpatterns = [
    path("clock-in/", ClockInAPIView.as_view(), name="check-in"),
    path("clock-out/", ClockOutAPIView.as_view(), name="check-out"),
    path("attendance/", AttendanceView.as_view(), name="attendance-list"),
    path("attendance/<int:pk>", AttendanceView.as_view(), name="attendance-detail"),
    path(
        "attendance/list/<str:type>", AttendanceView.as_view(), name="attendance-list"
    ),
    path("attendance-validate/<int:pk>", ValidateAttendanceView.as_view(), name=""),
    path(
        "attendance-request/",
        AttendanceRequestView.as_view(),
        name="attendance-request-view",
    ),
    path(
        "attendance-request/<int:pk>",
        AttendanceRequestView.as_view(),
        name="attendance-request-view",
    ),
    path(
        "attendance-request-approve/<int:pk>",
        AttendanceRequestApproveView.as_view(),
        name="",
    ),
    path(
        "attendance-request-cancel/<int:pk>",
        AttendanceRequestCancelView.as_view(),
        name="",
    ),
    path("overtime-approve/<int:pk>", OvertimeApproveView.as_view(), name=""),
    path(
        "attendance-hour-account/<int:pk>/", AttendanceOverTimeView.as_view(), name=""
    ),
    path("attendance-hour-account/", AttendanceOverTimeView.as_view(), name=""),
    path("late-come-early-out-view/", LateComeEarlyOutView.as_view(), name=""),
    path("attendance-activity/", AttendanceActivityView.as_view(), name=""),
    path("today-attendance/", TodayAttendance.as_view(), name=""),
    path("offline-employees/count/", OfflineEmployeesCountView.as_view(), name=""),
    path("offline-employees/list/", OfflineEmployeesListView.as_view(), name=""),
    path("permission-check/attendance", AttendancePermissionCheck.as_view()),
    path("checking-in", CheckingStatus.as_view()),
    path("offline-employee-mail-send", OfflineEmployeeMailsend.as_view()),
    path("converted-mail-template", ConvertedMailTemplateConvert.as_view()),
    path("mail-templates", MailTemplateView.as_view()),
]
