from django.urls import include, path

urlpatterns = [
    path("auth/", include("moared_api.api_urls.auth.urls")),
    path("asset/", include("moared_api.api_urls.asset.urls")),
    path("base/", include("moared_api.api_urls.base.urls")),
    path("employee/", include("moared_api.api_urls.employee.urls")),
    path("notifications/", include("moared_api.api_urls.notifications.urls")),
    path("payroll/", include("moared_api.api_urls.payroll.urls")),
    path("attendance/", include("moared_api.api_urls.attendance.urls")),
    path("leave/", include("moared_api.api_urls.leave.urls")),
]
