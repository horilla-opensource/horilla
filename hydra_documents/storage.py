from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateDocumentStorage(FileSystemStorage):
    """Filesystem storage with no public URL and a settings-driven root."""

    @property
    def base_location(self):
        return Path(settings.HYDRA_PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        # Unlike Django's cached location, this follows override_settings and
        # prevents one tenant/test root from leaking into the next operation.
        return str(self.base_location.resolve())

    def url(self, name):
        raise ValueError("Private documents do not have public URLs.")


private_document_storage = PrivateDocumentStorage(base_url=None)


class QuarantineStorage(PrivateDocumentStorage):
    """Separate, non-public storage for uploads that are not yet trusted."""

    @property
    def base_location(self):
        return Path(settings.HYDRA_DOCUMENT_QUARANTINE_ROOT)


quarantine_storage = QuarantineStorage(base_url=None)
