from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _trans

from horilla.decorators import (
    check_integration_enabled,
    login_required,
    permission_required,
)
from horilla_meet.filters import GoogleMeetingFilter
from horilla_meet.form import GoogleCloudCredentialForm, GoogleMeetingForm
from horilla_meet.models import GoogleCloudCredential, GoogleCredential, GoogleMeeting
from horilla_views.generic.cbv import views

# -------------------------------------- Google Credentials --------------------------------


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlecloudcredential"), name="dispatch"
)
class GMeetCredentialSectionView(views.HorillaSectionView):
    """
    View for displaying the Google Meet credentials section.

    Inherits from `HorillaSectionView` to manage the section for Google Cloud credentials in the user interface.
    Defines the URLs for navigation and the view, as well as the container element for the list.

    Attributes:
        nav_url (str): URL for nav view to the Google Meet settings.
        view_url (str): URL for the Google Meet credential list view.
        view_container_id (str): ID of the container that holds the list view.
        template_name (str): Template used to render the credential section view.
    """

    nav_url = reverse_lazy("gmeet-setting-nav")
    view_url = reverse_lazy("gmeet-setting-list-view")
    view_container_id = "credContainer"

    template_name = "gmeet_credentials/gmeet_credential_section_view.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlecloudcredential"), name="dispatch"
)
class GmeetCredentialNavView(views.HorillaNavView):
    """
    View for the Google Meet credentials nav view.

    Inherits from `HorillaNavView` to manage nav view for Google Cloud credentials. Handles dynamic attributes
    for creating credentials and updating modal behavior.

    Attributes:
        nav_title (str): The title of the nav view.
        search_swap_target (str): The target element to swap when performing searches.
        create_attrs (str): Attributes for create button for creating a new Google Cloud credential.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.create_attrs = f"""
            hx-get="{reverse_lazy('create-gmeet-credentials')}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
        """

    nav_title = _trans("Google Cloud Credentials")
    search_swap_target = "#credContainer"
    search_url = None


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlecloudcredential"), name="dispatch"
)
class GmeetCredentialListView(views.HorillaListView):
    """
    View for listing Google Meet credentials.

    Inherits from `HorillaListView` to manage the listing of Google Cloud credentials with actions like edit and delete.
    Defines how credentials are presented in the list (columns and actions) and handles interaction with the data.

    Attributes:
        model (Model): The model for Google Cloud credentials.
        columns (list): List of tuples defining the columns for the credential list view.
        actions (list): List of dictionaries defining the actions available for each row (edit, delete).
        row_attrs (str): Attributes for the rows in the list view.
        header_attrs (dict): Attributes for the header in the list view.
    """

    model = GoogleCloudCredential
    view_id = "credContainer"
    bulk_select_option = False

    columns = [
        ("Project ID", "project_id"),
        ("Client ID", "get_client_id_col"),
        ("Client Secret", "get_client_secret_col"),
        ("Redirect URIs", "get_redirect_url"),
        ("Company", "company_id"),
    ]

    actions = [
        {
            "action": _trans("Edit"),
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-50"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_update_url}"
                hx-target="#genericModalBody"
                """,
        },
        {
            "action": _trans("Delete"),
            "icon": "trash",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-50 text-danger"
                hx-confirm="Are you sure you want to delete this credential?"
                hx-post="{get_delete_url}"
                hx-swap="outerHTML swap:0.5s"
                hx-target = "closest tr"
                hx-on-htmx-after-request="reloadMessage(this);"
                """,
        },
    ]
    row_attrs = """
        class = "fade-me-out"
        data-column = ""
    """
    header_attrs = {
        "action": "style='width:100px;'",
        "get_redirect_url": "style='width:300px !important;'",
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.add_googlecloudcredential"), name="dispatch"
)
class GoogleCredentialsFormView(views.HorillaFormView):
    """
    View for creating or updating Google Cloud credentials.

    Inherits from `HorillaFormView` to manage the form for creating or updating Google Cloud credentials.
    Handles form validation, success, and failure responses. Displays success or error messages accordingly.

    Attributes:
        form_class (Form): The form class used to create or update credentials.
        model (Model): The model associated with the form (Google Cloud Credential).
        new_display_title (str): The title shown when creating new credentials.
        template_name (str): The template used to render the form view.
    """

    form_class = GoogleCloudCredentialForm
    model = GoogleCloudCredential
    new_display_title = _trans("Create Google Cloud Credentials")
    template_name = "generic/horilla_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = GoogleCloudCredential.objects.filter(pk=self.kwargs["pk"]).first()
        kwargs["instance"] = instance
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: GoogleCloudCredentialForm) -> views.HttpResponse:
        if form.is_valid():
            message = "Google cloud credential added"
            if form.instance.pk:
                message = "Google cloud credential updated"
            form.save()

            messages.success(self.request, _trans(message))
            return self.HttpResponse()

        return super().form_valid(form)


# -------------------------------------- Google Meetings --------------------------------


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("horilla_meet.add_googlemeeting"), name="dispatch"
)
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
class GmeetFormView(views.HorillaFormView):
    """
    View for creating or updating Google Meet meetings.

    Inherits from `HorillaFormView` to manage the form for creating or updating Google Meet meetings.
    Handles form validation, success, and failure responses. Displays success or error messages accordingly.

    Attributes:
        form_class (Form): The form class used to create or update Google Meet.
        model (Model): The model associated with the form (GoogleMeeting).
        new_display_title (str): The title shown when creating a new Google Meet.
        template_name (str): The template used to render the form view.
    """

    form_class = GoogleMeetingForm
    model = GoogleMeeting
    new_display_title = _trans("Create Google Meet")
    template_name = "gmeet/meet_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = GoogleMeeting.objects.filter(pk=self.kwargs["pk"]).first()
        kwargs["instance"] = instance
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: GoogleMeetingForm) -> views.HttpResponse:
        if form.is_valid():
            message = "Google cloud credential added"
            if form.instance.pk:
                message = "Google cloud credential updated"
            form.save()

            messages.success(self.request, _trans(message))
            return self.HttpResponse()

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlemeeting"), name="dispatch"
)
class GmeetSectionView(views.HorillaSectionView):
    """
    View for displaying the Google Meet section.

    Inherits from `HorillaSectionView` to manage the section for Google Meet in the user interface.
    Provides context regarding the user's credentials and renders the associated template.

    Attributes:
        nav_url (str): URL for nav view to the Google Meet section.
        view_url (str): URL for the Google Meet section view.
        view_container_id (str): ID of the container that holds the view's list.
        template_name (str): Template used to render the Google Meet section view.
    """

    nav_url = reverse_lazy("gmeet-nav-view")
    view_url = reverse_lazy("gmeet-list-view")
    view_container_id = "listContainer"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        has_credentials = GoogleCredential.objects.filter(
            employee_id=self.request.user.employee_get
        ).exists()
        context["has_credentials"] = has_credentials
        return context

    template_name = "gmeet/gmeet_view.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlemeeting"), name="dispatch"
)
class GmeetNavView(views.HorillaNavView):
    """
    Nav view for Google Meet.

    Inherits from `HorillaNavView` to manage nav bar for Google Meet view. Handles dynamic attributes for creating
    a Google Meet based on whether the user has credentials.

    Attributes:
        nav_title (str): The title of the nav bar.
        search_url (str): URL for searching Google Meet items.
        search_swap_target (str): The target element to swap when performing searches.
        create_attrs (str): Dynamic attributes for handling the creation of Google Meet meetings.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        has_credentials = GoogleCredential.objects.filter(
            employee_id=self.request.user.employee_get
        ).exists()
        if has_credentials:
            self.create_attrs = f"""
                hx-get="{reverse_lazy('create-gmeet')}"
                hx-target="#genericModalBody"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
            """
        else:
            self.create_attrs = f"""
            href ="{reverse_lazy('create-google-meet')}"
            """

    nav_title = _trans("Google Meet View")
    search_url = reverse_lazy("gmeet-list-view")
    filter_instance = GoogleMeetingFilter()
    filter_form_context_name = "form"
    filter_body_template = "gmeet/filter.html"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlemeeting"), name="dispatch"
)
class GmeetListView(views.HorillaListView):
    """
    View for listing Google Meetings.

    Inherits from `HorillaListView` to manage the listing of Google meetings with actions like edit, delete, and view meeting link.

    Attributes:
        model (Model): The model for Google Meetings.
        search_url (str): URL for searching Google Meetings.
        filter_class (Filter): The filter class for Google Meetings.
        columns (list): List of tuples defining the columns for the meeting list view.
        actions (list): List of dictionaries defining the actions available for each row (meeting link, edit, delete).
        header_attrs (dict): Attributes for the header in the list view.
        row_attrs (str): Attributes for the rows in the list view.
    """

    model = GoogleMeeting
    search_url = reverse_lazy("gmeet-list-view")
    filter_class = GoogleMeetingFilter
    columns = [
        ("Title", "get_title_column"),
        ("Employee", "employee_id"),
        ("Start Time", "start_time_str"),
        ("Duration", "duration"),
        ("Description", "description"),
        ("Attendees", "get_attendees_column"),
    ]

    actions = [
        {
            "action": _trans("Meeting Link"),
            "icon": "link-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-50"
                href={meet_url}
                target="_blank"
                """,
        },
        {
            "action": _trans("Edit"),
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-50"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_update_url}"
                hx-target="#genericModalBody"
                """,
        },
        {
            "action": _trans("Delete"),
            "icon": "trash",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-50 text-danger"
                hx-confirm="Are you sure you want to delete this meeting?"
                hx-post="{get_delete_url}"
                hx-swap="outerHTML swap:0.5s"
                hx-target = "closest tr"
                hx-on-htmx-after-request="reloadMessage(this);"
                """,
        },
    ]

    header_attrs = {
        "duration": "style='width:100px;'",
        "action": "style='width:150px;'",
        "get_title_column": "style='width:200px !important;'",
    }

    row_attrs = """
        class = "oh-permission-table__tr oh-permission-table__tr oh-permission-table--collapsed fade-me-out oh-sticky-table__tr"
        hx-get="{detailed_url}?instance_ids={ordered_ids}"
        hx-target="#genericModalBody"
        data-toggle="oh-modal-toggle"
        data-target="#genericModal"
    """


@method_decorator(login_required, name="dispatch")
@method_decorator(check_integration_enabled(app_name="horilla_meet"), name="dispatch")
@method_decorator(
    permission_required("horilla_meet.view_googlemeeting"), name="dispatch"
)
class GmeetDetailedView(views.HorillaDetailedView):
    """
    Detailed view for Google Meetings.

    Inherits from `HorillaDetailedView` to manage the detailed view of a specific Google Meeting.
    Displays information such as the meeting URL, event ID, start time, end time, and description.

    Attributes:
        model (Model): The model for Google Meetings.
        title (str): The title for the detailed view.
        template_name (str): The template used to render the detailed view.
        cols (dict): A dictionary defining the column span for the detailed view layout.
        body (list): A list of tuples defining the fields to display in the detailed view.
        actions (list): A list of dictionaries defining actions like edit, join meeting, and delete.
    """

    model = GoogleMeeting
    title = "Google Meeting"
    # template_name = "gmeet/gmeet_detailed_view.html"
    cols = {"description": 12}
    body = [
        ("Meeting URL", "meet_url"),
        ("Event ID", "event_id"),
        ("Start Time", "start_time"),
        ("End Time", "end_time"),
        ("Description", "description"),
    ]

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
            hx-get="{get_update_url}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            class="oh-btn oh-btn--info w-50"
            """,
        },
        {
            "action": "Join Meeting",
            "icon": "link-outline",
            "attrs": """
                class="oh-btn oh-btn--warning text-white w-50"
                href={meet_url}
                target="_blank"
            """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
            class="oh-btn oh-btn--danger w-50 delete_button"
            hx-confirm="Are you sure you want to delete this meeting?"
            hx-post="{get_delete_url}?detail_view=true"
            hx-target = "#listContainer"
            hx-on-htmx-after-request="reloadMessage(this); nextButtonClick()"
            """,
        },
    ]
