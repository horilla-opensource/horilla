import uuid
from datetime import timedelta

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from horilla_meet.models import GoogleCredential


def get_google_credentials(request):
    """Fetches and refreshes Google credentials for the logged-in user."""

    try:
        creds = GoogleCredential.objects.get(employee_id=request.user.employee_get)
    except GoogleCredential.DoesNotExist:
        raise Exception("Google credentials not found for the user.")

    credentials = Credentials(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=creds.scopes.split(","),
    )

    if credentials.expired:
        try:
            credentials.refresh(Request())
            creds.token = credentials.token
            creds.save()
        except Exception as e:
            raise Exception(f"Failed to refresh Google credentials: {e}")

    return credentials


def create_calendar_event(request, data):
    """Create a Google Calendar event from a given data."""

    credentials = get_google_credentials(request)

    service = build("calendar", "v3", credentials=credentials)
    attendees = data["attendees"]

    event = {
        "summary": data["title"],
        "description": data["description"],
        "start": {
            "dateTime": data["start_time"].isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "end": {
            "dateTime": (
                data["start_time"] + timedelta(minutes=data["duration"])
            ).isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "attendees": [{"email": mail} for mail in attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    try:
        created_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
                sendNotifications=True,
            )
            .execute()
        )
    except Exception as e:
        raise Exception(f"Failed to create calendar event: {e}")

    return created_event


def update_calendar_event(request, data, event_id=None):
    """Updates an existing Google Calendar event."""

    if not event_id:
        raise Exception("Cannot update event: event_id is missing.")

    credentials = get_google_credentials(request)

    service = build("calendar", "v3", credentials=credentials)
    attendees = data["attendees"]

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
    except Exception as e:
        raise Exception(f"Failed to retrieve event: {e}")

    event["summary"] = data["title"]
    event["description"] = data["description"]
    event["start"] = {
        "dateTime": data["start_time"].isoformat(),
        "timeZone": settings.TIME_ZONE,
    }
    event["end"] = {
        "dateTime": (
            data["start_time"] + timedelta(minutes=data["duration"])
        ).isoformat(),
        "timeZone": settings.TIME_ZONE,
    }
    event["attendees"] = [{"email": attendee} for attendee in attendees]

    try:
        updated_event = (
            service.events()
            .update(
                calendarId="primary",
                eventId=event_id,
                body=event,
                sendUpdates="all",
            )
            .execute()
        )
    except Exception as e:
        raise Exception(f"Failed to update calendar event: {e}")

    return updated_event
