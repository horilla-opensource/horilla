"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path

from base.views import object_delete
from helpdesk import views
from helpdesk.cbv import department_managers, faq, pipeline, tags, ticket_type
from helpdesk.models import FAQ, FAQCategory, Ticket

urlpatterns = [
    path("ticket-list/", ticket_type.TicketsListView.as_view(), name="ticket-list"),
    path("ticket-nav/", ticket_type.TicketsNavView.as_view(), name="ticket-nav"),
    path(
        "ticket-create-form/",
        ticket_type.TicketTypeCreateForm.as_view(),
        name="ticket-create-form",
    ),
    path(
        "ticket-update-form/<int:pk>",
        ticket_type.TicketTypeCreateForm.as_view(),
        name="ticket-update-form",
    ),
    path("faq-category-view/", views.faq_category_view, name="faq-category-view"),
    # path("faq-category-create/", views.faq_category_create, name="faq-category-create"),
    path(
        "faq-category-create/",
        faq.FaqCategoryCreateFormView.as_view(),
        name="faq-category-create",
    ),
    path(
        "faq-category-update/<int:pk>/",
        faq.FaqCategoryCreateFormView.as_view(),
        name="faq-category-update",
    ),
    # path(
    #     "faq-category-update/<int:id>/",
    #     views.faq_category_update,
    #     name="faq-category-update",
    # ),
    path(
        "faq-category-delete/<int:id>/",
        views.faq_category_delete,
        name="faq-category-delete",
    ),
    path("faq-category-search/", views.faq_category_search, name="faq-category-search"),
    path(
        "faq-view/<int:obj_id>/",
        views.faq_view,
        name="faq-view",
        kwargs={"model": FAQCategory},
    ),
    path(
        "faq-create/<int:cat_id>/", faq.FaqCreateFormView.as_view(), name="faq-create"
    ),
    # path("faq-create/<int:cat_id>/", views.create_faq, name="faq-create"),
    path("faq-update/<int:pk>/", faq.FaqCreateFormView.as_view(), name="faq-update"),
    # path("faq-update/<int:id>", views.faq_update, name="faq-update"),
    path("faq-search/", views.faq_search, name="faq-search"),
    path("faq-filter/<int:id>/", views.faq_filter, name="faq-filter"),
    path("faq-suggestion/", views.faq_suggestion, name="faq-suggestion"),
    path(
        "faq-delete/<int:id>/",
        views.faq_delete,
        name="faq-delete",
    ),
    # path("ticket-view/", views.ticket_view, name="ticket-view"),
    path("ticket-view/", pipeline.TicketPipelineView.as_view(), name="ticket-view"),
    path(
        "ticket-pipeline-nav/",
        pipeline.TicketPipelineNav.as_view(),
        name="ticket-pipeline-nav",
    ),
    path("get-ticket-tabs", pipeline.TicketTabView.as_view(), name="get-ticket-tabs"),
    path("ticket-tab/", pipeline.TicketTabView.as_view(), name="ticket-tab"),
    path("ticket-tab-list/", pipeline.TicketListView.as_view(), name="ticket-tab-list"),
    path("ticket-tab-card/", pipeline.TicketCardView.as_view(), name="ticket-tab-card"),
    # path("ticket-pipeline-view/", pipeline.TicketPipelineTabView.as_view(), name="ticket-pipeline-view"),
    path(
        "ticket-create",
        ticket_type.TicketsCreateFormView.as_view(),
        name="ticket-create",
    ),
    # path("ticket-create", views.ticket_create, name="ticket-create"),
    path(
        "ticket-update/<int:pk>/",
        ticket_type.TicketsCreateFormView.as_view(),
        name="ticket-update",
    ),
    # path("ticket-update/<int:ticket_id>", views.ticket_update, name="ticket-update"),
    path("ticket-archive/<int:ticket_id>", views.ticket_archive, name="ticket-archive"),
    path(
        "change-ticket-status/<int:ticket_id>/",
        views.change_ticket_status,
        name="change-ticket-status",
    ),
    path(
        "ticket-status-change/<int:ticket_id>/",
        views.ticket_status_change,
        name="ticket-status-change",
    ),
    path("ticket-delete/<int:ticket_id>", views.ticket_delete, name="ticket-delete"),
    path("ticket-filter", views.ticket_filter, name="ticket-filter"),
    path(
        "ticket-detail/<int:ticket_id>/",
        views.ticket_detail,
        name="ticket-detail",
        kwargs={"model": Ticket},
    ),
    path(
        "ticket-individual-view/<int:ticket_id>",
        views.ticket_individual_view,
        name="ticket-individual-view",
    ),
    path(
        "view-ticket-claim-request/<int:ticket_id>",
        views.view_ticket_claim_request,
        name="view-ticket-claim-request",
    ),
    path("ticket-change-tag", views.ticket_update_tag, name="ticket-change-tag"),
    path(
        "ticket-change-raised-on/<int:ticket_id>",
        views.ticket_change_raised_on,
        name="ticket-change-raised-on",
    ),
    path(
        "ticket-change-assignees/<int:ticket_id>",
        views.ticket_change_assignees,
        name="ticket-change-assignees",
    ),
    path("ticket-create-tag", views.create_tag, name="ticket-create-tag"),
    path("remove-tag", views.remove_tag, name="remove-tag"),
    path(
        "view-ticket-document/<int:doc_id>",
        views.view_ticket_document,
        name="view-ticket-document",
    ),
    path("comment-create/<int:ticket_id>", views.comment_create, name="comment-create"),
    path("comment-edit/", views.comment_edit, name="comment-edit"),
    path(
        "comment-delete/<int:comment_id>/", views.comment_delete, name="comment-delete"
    ),
    path("get-raised-on", views.get_raised_on, name="get-raised-on"),
    path("claim-ticket/<int:id>", views.claim_ticket, name="claim-ticket"),
    path(
        "approve-claim-request/<int:req_id>",
        views.approve_claim_request,
        name="approve-claim-request",
    ),
    path(
        "tickets-select-filter",
        views.tickets_select_filter,
        name="tickets-select-filter",
    ),
    path(
        "tickets-bulk-archive", views.tickets_bulk_archive, name="tickets-bulk-archive"
    ),
    path("tickets-bulk-delete", views.tickets_bulk_delete, name="tickets-bulk-delete"),
    # path(
    #     "department-manager-create/",
    #     views.create_department_manager,
    #     name="department-manager-create",
    # ),
    path(
        "settings/helpdesk-tag-list/",
        tags.TagsListView.as_view(),
        name="helpdesk-tag-list",
    ),
    path(
        "settings/helpdesk-tag-nav/",
        tags.TagsNavView.as_view(),
        name="helpdesk-tag-nav",
    ),
    path(
        "settings/create-helpdesk-tag/",
        tags.TagsFormView.as_view(),
        name="create-helpdesk-tag",
    ),
    path(
        "settings/update-helpdesk-tag/<int:pk>/",
        tags.TagsFormView.as_view(),
        name="update-helpdesk-tag",
    ),
    path(
        "department-manager-create/",
        department_managers.DepartmentManagersFormView.as_view(),
        name="department-manager-create",
    ),
    path(
        "settings/department-manager-list/",
        department_managers.DepartmentManagersListView.as_view(),
        name="department-manager-list",
    ),
    path(
        "settings/department-manager-nav/",
        department_managers.DepartmentManagersNav.as_view(),
        name="department-manager-nav",
    ),
    path(
        "department-manager-update/<int:dep_id>",
        views.update_department_manager,
        name="department-manager-update",
    ),
    path(
        "department-manager-update-view/<int:pk>/",
        department_managers.DepartmentManagersFormView.as_view(),
        name="department-manager-update-view",
    ),
    path(
        "department-manager-delete/<int:dep_id>",
        views.delete_department_manager,
        name="department-manager-delete",
    ),
    path(
        "update-priority/<int:ticket_id>",
        views.update_priority,
        name="update-priority",
    ),
    path("ticket-type-view/", views.ticket_type_view, name="ticket-type-view"),
    path("ticket-type-create", views.ticket_type_create, name="ticket-type-create"),
    path(
        "ticket-type-update/<int:t_type_id>",
        views.ticket_type_update,
        name="ticket-type-update",
    ),
    path(
        "ticket-type-delete/<int:t_type_id>",
        views.ticket_type_delete,
        name="ticket-type-delete",
    ),
    path(
        "department-manager-view/",
        views.view_department_managers,
        name="department-manager-view",
    ),
    path(
        "get-department-employee",
        views.get_department_employees,
        name="get-department-employee",
    ),
    path(
        "delete-ticket-document/<int:doc_id>",
        views.delete_ticket_document,
        name="delete-ticket-document",
    ),
    path("load-faqs/", views.load_faqs, name="load-faqs"),
    path(
        "ticket-file-upload/<int:id>/",
        views.ticket_file_upload,
        name="ticket-file-upload",
    ),
]
