"""URL routes for the tour engine — public API + Settings admin CRUD."""

from django.urls import path

from horilla_tour import views

urlpatterns = [
    # ---- Public JSON API (consumed by tourController.js) ----
    path("tour/api/active/", views.tour_active, name="tour-active"),
    path("tour/api/progress/", views.tour_progress, name="tour-progress"),
    # ---- Settings admin: Tours ----
    path("settings/tours/", views.tour_settings_page, name="tour-section"),
    path("tour-nav/", views.TourNav.as_view(), name="tour-nav"),
    path("tour-list/", views.TourList.as_view(), name="tour-list"),
    path("tour-create-form/", views.TourFormView.as_view(), name="tour-create-form"),
    path(
        "tour-update-form/<int:pk>/",
        views.TourFormView.as_view(),
        name="tour-update-form",
    ),
    # ---- Settings admin: Steps (managed inside the tour modal) ----
    path("tour-steps/", views.tour_steps, name="tour-steps"),
    path("tour-step-form/", views.tour_step_form, name="tour-step-form"),
    path("tour-step-delete/", views.tour_step_delete, name="tour-step-delete"),
]
