"""
horilla_api/urls/leave/urls.py
"""

from django.urls import path

from horilla_api.api_views.leave.views import *

urlpatterns = [
    path("available-leave/", EmployeeAvailableLeaveGetAPIView.as_view()),
    path("user-request/", EmployeeLeaveRequestGetCreateAPIView.as_view()),
    path("user-request/<int:pk>/", EmployeeLeaveRequestUpdateDeleteAPIView.as_view()),
    path("leave-type/", LeaveTypeGetCreateAPIView.as_view()),
    path("leave-type/<int:pk>/", LeaveTypeGetUpdateDeleteAPIView.as_view()),
    path("allocation-request/", LeaveAllocationRequestGetCreateAPIView.as_view()),
    path(
        "allocation-request/<int:pk>/",
        LeaveAllocationRequestGetUpdateDeleteAPIView.as_view(),
    ),
    path("assign-leave/", AssignLeaveGetCreateAPIView.as_view()),
    path("assign-leave/<int:pk>/", AssignLeaveGetUpdateDeleteAPIView.as_view()),
    path("request/", LeaveRequestGetCreateAPIView.as_view()),
    path("request/<int:pk>/", LeaveRequestGetUpdateDeleteAPIView.as_view()),
    path("company-leave/", CompanyLeaveGetCreateAPIView.as_view()),
    path("company-leave/<int:pk>/", CompanyLeaveGetUpdateDeleteAPIView.as_view()),
    path("holiday/", HolidayGetCreateAPIView.as_view()),
    path("holiday/<int:pk>/", HolidayGetUpdateDeleteAPIView.as_view()),
    path("approve/<int:pk>/", LeaveRequestApproveAPIView.as_view()),
    path("reject/<int:pk>/", LeaveRequestRejectAPIView.as_view()),
    path("cancel/<int:pk>/", LeaveRequestCancelAPIView.as_view()),
    path("allocation-approve/<int:pk>/", LeaveAllocationApproveAPIView.as_view()),
    path("allocation-reject/<int:pk>/", LeaveAllocationRequestRejectAPIView.as_view()),
    path("request-bulk-action/", LeaveRequestBulkApproveDeleteAPIview.as_view()),
    path("user-allocation-request/", EmployeeLeaveAllocationGetCreateAPIView.as_view()),
    path(
        "user-allocation-request/<int:pk>/",
        EmployeeLeaveAllocationUpdateDeleteAPIView.as_view(),
    ),
    path("status/", LeaveRequestedApprovedCountAPIView.as_view()),
    path(
        "employee-leave-type/<int:pk>/", EmployeeAvailableLeaveTypeGetAPIView.as_view()
    ),
    path("check-type/", LeaveTypeGetPermissionCheckAPIView.as_view()),
    path("check-allocation/", LeaveAllocationGetPermissionCheckAPIView.as_view()),
    path("check-request/", LeaveRequestGetPermissionCheckAPIView.as_view()),
    path("check-assign/", LeaveAssignGetPermissionCheckAPIView.as_view()),
    path("check-perm/", LeavePermissionCheckAPIView.as_view()),
]
