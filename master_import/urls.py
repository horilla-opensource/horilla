from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="master-import"),
    path("upload/", views.upload, name="master-import-upload"),
    path(
        "template/<str:dataset>/",
        views.template_download,
        name="master-import-template",
    ),
    path("history/", views.history, name="master-import-history"),
    path("<int:job_id>/map/", views.map_columns, name="master-import-map"),
    path("<int:job_id>/review/", views.review, name="master-import-review"),
    path("<int:job_id>/edits/", views.save_edits, name="master-import-edits"),
    path("<int:job_id>/check/", views.check, name="master-import-check"),
    path(
        "<int:job_id>/check-progress/",
        views.check_progress,
        name="master-import-check-progress",
    ),
    path(
        "<int:job_id>/download/<str:kind>/",
        views.download_records,
        name="master-import-download",
    ),
    path("<int:job_id>/run/", views.run, name="master-import-run"),
    path("<int:job_id>/done/", views.done, name="master-import-done"),
    path("<int:job_id>/errors/", views.error_file, name="master-import-errors"),
]
