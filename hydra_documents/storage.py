from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateDocumentStorage(FileSystemStorage):
    """Filesystem storage with no public URL and a settings-driven root."""

    @property
    def base_location(self):
        return Path(settings.HYDRA_PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise ValueError("Private documents do not have public URLs.")


private_document_storage = PrivateDocumentStorage(base_url=None)
