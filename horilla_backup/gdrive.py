import json
import os
from datetime import datetime, timedelta

from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_credentials_from_model(google_drive_backup):
    """
    Get or refresh OAuth credentials from the model.
    Returns credentials object or None if authorization is needed.
    """
    if not google_drive_backup.access_token:
        return None

    if not google_drive_backup.oauth_credentials_file or not hasattr(
        google_drive_backup.oauth_credentials_file, "path"
    ):
        raise Exception(
            "OAuth credentials file not found. Please upload it in the settings."
        )

    # Load client credentials from file
    oauth_file_path = google_drive_backup.oauth_credentials_file.path
    with open(oauth_file_path, "r") as f:
        client_config = json.load(f)

    client_id = client_config["web"]["client_id"]
    client_secret = client_config["web"]["client_secret"]
    token_uri = client_config["web"]["token_uri"]

    creds = Credentials(
        token=google_drive_backup.access_token,
        refresh_token=google_drive_backup.refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
    )

    # Check if token is expired or about to expire (within 5 minutes)
    if google_drive_backup.token_expiry:
        expiry_time = google_drive_backup.token_expiry
        # Ensure both datetimes are timezone-aware for comparison
        now = timezone.now()
        if timezone.is_naive(expiry_time):
            # If expiry is naive, make it timezone-aware (assume UTC)
            expiry_time = timezone.make_aware(expiry_time, timezone.utc)

        # Compare timezone-aware datetimes
        if now >= expiry_time - timedelta(minutes=5):
            # Token expired or about to expire, refresh it
            creds = refresh_credentials(google_drive_backup, creds)

    return creds


def refresh_credentials(google_drive_backup, creds):
    """
    Refresh OAuth credentials and update the model.
    """
    try:
        # Load client credentials from file
        oauth_file_path = google_drive_backup.oauth_credentials_file.path
        with open(oauth_file_path, "r") as f:
            client_config = json.load(f)

        client_id = client_config["web"]["client_id"]
        client_secret = client_config["web"]["client_secret"]
        token_uri = client_config["web"]["token_uri"]

        # Create new credentials object with client info for refresh
        from google.oauth2.credentials import Credentials as OAuthCredentials

        refresh_creds = OAuthCredentials(
            token=None,  # Will be refreshed
            refresh_token=creds.refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
        )

        # Refresh the token
        refresh_creds.refresh(Request())

        # Update model with new tokens
        google_drive_backup.access_token = refresh_creds.token
        if refresh_creds.refresh_token:
            google_drive_backup.refresh_token = refresh_creds.refresh_token
        if refresh_creds.expiry:
            # Make datetime timezone-aware if it's naive
            from django.utils import timezone as tz

            if tz.is_naive(refresh_creds.expiry):
                google_drive_backup.token_expiry = tz.make_aware(
                    refresh_creds.expiry, tz.utc
                )
            else:
                google_drive_backup.token_expiry = refresh_creds.expiry
        google_drive_backup.save()

        return refresh_creds
    except Exception as e:
        raise Exception(f"Failed to refresh credentials: {str(e)}")


def get_authorization_url(oauth_credentials_file_path, redirect_uri):
    """
    Generate OAuth authorization URL.
    Returns (authorization_url, flow) tuple.
    """
    with open(oauth_credentials_file_path, "r") as f:
        client_config = json.load(f)

    # Use Flow for web applications
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=redirect_uri)

    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )

    return authorization_url, flow, state


def exchange_code_for_tokens(flow, authorization_response_url):
    """
    Exchange authorization code for tokens.
    Returns credentials object.
    """
    flow.fetch_token(authorization_response_url=authorization_response_url)
    return flow.credentials


def authenticate(oauth_credentials_file):
    """
    Authenticate using OAuth credentials file.
    This is used for validation in forms.
    """
    try:
        with open(oauth_credentials_file, "r") as f:
            client_config = json.load(f)

        # Validate that it's a web OAuth credentials file
        if "web" not in client_config:
            raise ValueError("Invalid OAuth credentials file. Expected 'web' key.")

        required_keys = ["client_id", "client_secret", "auth_uri", "token_uri"]
        for key in required_keys:
            if key not in client_config["web"]:
                raise ValueError(f"Missing required key: {key}")

        return True
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON file.")
    except Exception as e:
        raise ValueError(f"Invalid OAuth credentials file: {str(e)}")


def upload_file(file_path, google_drive_backup, parent_folder_id):
    """
    Upload file to Google Drive using OAuth credentials.
    """
    if not os.path.exists(file_path):
        raise Exception(f"File does not exist: {file_path}")

    file_size = os.path.getsize(file_path)
    print(
        f"Uploading file: {os.path.basename(file_path)} ({file_size} bytes) to folder: {parent_folder_id}"
    )

    creds = get_credentials_from_model(google_drive_backup)

    if not creds or not creds.valid:
        raise Exception("OAuth credentials are not valid. Please re-authorize.")

    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": os.path.basename(file_path), "parents": [parent_folder_id]}

    # Use resumable upload for large files (>5MB)
    # For smaller files, regular upload is fine
    if file_size > 5 * 1024 * 1024:  # 5MB
        print("Using resumable upload for large file")
        media = MediaFileUpload(file_path, resumable=True, chunksize=1024 * 1024)
    else:
        print("Using regular upload for small file")
        media = MediaFileUpload(file_path, resumable=False)

    try:
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        file_id = file.get("id")
        print(f"File uploaded successfully. Google Drive file ID: {file_id}")
        return file_id
    except Exception as e:
        error_msg = str(e)
        print(f"Upload failed: {error_msg}")
        # Check for specific errors
        if "quota" in error_msg.lower() or "storageQuotaExceeded" in error_msg:
            raise Exception(
                "Google Drive storage quota exceeded. Please free up space or upgrade your plan."
            )
        elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            raise Exception(
                f"Permission denied. Please ensure the authenticated user has write access to folder ID: {parent_folder_id}"
            )
        else:
            raise Exception(f"Upload failed: {error_msg}")
