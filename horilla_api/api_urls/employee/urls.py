from django.urls import path

from ...api_views.employee import views as views

urlpatterns = [
    path("employees/", views.EmployeeAPIView.as_view(), name="employees-list"),
    path(
        "employees/<int:pk>/", views.EmployeeAPIView.as_view(), name="employee-detail"
    ),
    path(
        "employee-type/<int:pk>", views.EmployeeTypeAPIView.as_view(), name="employees"
    ),
    path("employee-type/", views.EmployeeTypeAPIView.as_view(), name="employees"),
    path(
        "list/employees/",
        views.EmployeeListAPIView.as_view(),
        name="employee-list-detailed",
    ),  # Alternative endpoint for listing employees
    path(
        "employee-bank-details/<int:pk>/",
        views.EmployeeBankDetailsAPIView.as_view(),
        name="employee-bank-details-detail",
    ),
    path(
        "employee-work-information/",
        views.EmployeeWorkInformationAPIView.as_view(),
        name="employee-work-information-list",
    ),
    path(
        "employee-work-information/<int:pk>/",
        views.EmployeeWorkInformationAPIView.as_view(),
        name="employee-work-information-detail",
    ),
    path(
        "employee-work-info-export/",
        views.EmployeeWorkInfoExportView.as_view(),
        name="employee-work-info-export",
    ),
    path(
        "employee-work-info-import/",
        views.EmployeeWorkInfoImportView.as_view(),
        name="employee-work-info-import",
    ),
    path(
        "employee-bulk-update/",
        views.EmployeeBulkUpdateView.as_view(),
        name="employee-bulk-update",
    ),
    path(
        "disciplinary-action/",
        views.DisciplinaryActionAPIView.as_view(),
        name="disciplinary-action-list",
    ),
    path(
        "disciplinary-action/<int:pk>/",
        views.DisciplinaryActionAPIView.as_view(),
        name="disciplinary-action-detail",
    ),
    path(
        "disciplinary-action-type/",
        views.ActiontypeView.as_view(),
        name="disciplinary-action-type",
    ),
    path(
        "disciplinary-action-type/<int:pk>/",
        views.ActiontypeView.as_view(),
        name="disciplinary-action-type",
    ),
    path("policies/", views.PolicyAPIView.as_view(), name="policy-list"),
    path("policies/<int:pk>/", views.PolicyAPIView.as_view(), name="policy-detail"),
    path(
        "document-request/",
        views.DocumentRequestAPIView.as_view(),
        name="document-request-list",
    ),
    path(
        "document-request/<int:pk>/",
        views.DocumentRequestAPIView.as_view(),
        name="document-request-detail",
    ),
    path(
        "document-bulk-approve-reject/",
        views.DocumentBulkApproveRejectAPIView.as_view(),
        name="document-bulk-approve-reject",
    ),
    path(
        "document-request-approve-reject/<int:id>/<str:status>/",
        views.DocumentRequestApproveRejectView.as_view(),
        name="document-request-approve-reject",
    ),
    path("documents/", views.DocumentAPIView.as_view(), name="document-list"),
    path(
        "documents/<int:pk>/", views.DocumentAPIView.as_view(), name="document-detail"
    ),
    path(
        "employee-bulk- archive/<str:is_active>/",
        views.EmployeeBulkArchiveView.as_view(),
        name="employee-bulk-archive",
    ),
    path(
        "employee-archive/<int:id>/<str:is_active>/",
        views.EmployeeArchiveView.as_view(),
        name="employee-archive",
    ),
    path(
        "employee-selector/",
        views.EmployeeSelectorView.as_view(),
        name="employee-selector",
    ),
    path("manager-check/", views.ReportingManagerCheck.as_view(), name="manager-check"),
]
