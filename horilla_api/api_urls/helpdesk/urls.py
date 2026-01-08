"""
horilla_api/api_urls/helpdesk/urls.py
"""

from django.urls import path

from horilla_api.api_views.helpdesk.views import *

urlpatterns = [
    # Ticket Type URLs
    path("ticket-type/", TicketTypeGetCreateAPIView.as_view()),
    path("ticket-type/<int:pk>/", TicketTypeGetUpdateDeleteAPIView.as_view()),
    # FAQ Category URLs
    path("faq-category/", FAQCategoryGetCreateAPIView.as_view()),
    path("faq-category/<int:pk>/", FAQCategoryGetUpdateDeleteAPIView.as_view()),
    # FAQ URLs
    path("faq/", FAQGetCreateAPIView.as_view()),
    path("faq/<int:pk>/", FAQGetUpdateDeleteAPIView.as_view()),
    path("faq/category/<int:category_id>/", FAQGetCreateAPIView.as_view()),
    # Ticket URLs
    path("ticket/", TicketGetCreateAPIView.as_view()),
    path("ticket/<int:pk>/", TicketGetUpdateDeleteAPIView.as_view()),
    path("ticket/<int:pk>/status/", TicketChangeStatusAPIView.as_view()),
    path("ticket/<int:pk>/archive/", TicketArchiveAPIView.as_view()),
    # Comment URLs
    path("ticket/<int:ticket_id>/comment/", CommentGetCreateAPIView.as_view()),
    path("comment/<int:pk>/", CommentGetUpdateDeleteAPIView.as_view()),
    # Attachment URLs
    path("ticket/<int:ticket_id>/attachment/", AttachmentGetCreateAPIView.as_view()),
    path("comment/<int:comment_id>/attachment/", AttachmentGetCreateAPIView.as_view()),
    path("attachment/<int:pk>/", AttachmentGetDeleteAPIView.as_view()),
    # Claim Request URLs
    path("claim-request/", ClaimRequestGetCreateAPIView.as_view()),
    path(
        "ticket/<int:ticket_id>/claim-request/", ClaimRequestGetCreateAPIView.as_view()
    ),
    path("claim-request/<int:pk>/approve/", ClaimRequestApproveAPIView.as_view()),
    path("claim-request/<int:pk>/reject/", ClaimRequestRejectAPIView.as_view()),
    # Department Manager URLs
    path("department-manager/", DepartmentManagerGetCreateAPIView.as_view()),
    path(
        "department-manager/<int:pk>/",
        DepartmentManagerGetUpdateDeleteAPIView.as_view(),
    ),
]
