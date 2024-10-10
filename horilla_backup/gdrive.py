import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def authenticate(service_account_file):
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    return creds


def upload_file(file_path, service_account_file, parent_folder_id):
    creds = authenticate(service_account_file)
    service = build("drive", "v3", credentials=creds)
    parent_folder_id = parent_folder_id

    file_metadata = {"name": os.path.basename(file_path), "parents": [parent_folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
