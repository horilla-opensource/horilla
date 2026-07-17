from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PortalEmailStorage(FileSystemStorage):
    """Non-public storage shared by web and maintenance processes."""

    @property
    def base_location(self):
        return Path(settings.HYDRA_PORTAL_EMAIL_MEDIA_ROOT)

    @property
    def location(self):
        return str(self.base_location.resolve())

    def url(self, name):
        raise ValueError("Portal email attachments do not have public URLs.")


portal_email_storage = PortalEmailStorage(base_url=None)
