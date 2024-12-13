# storages.py

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class CustomS3Boto3Storage(S3Boto3Storage):
    def _normalize_name(self, name):
        # Remove leading slashes
        name = name.lstrip('/')
        return super()._normalize_name(name)

    def url(self, name, parameters=None, expire=None, http_method=None):
        # Normalize the name
        name = self._normalize_name(name)

        # Handle empty names
        if not name:
            return settings.STATIC_URL  # Return the base static URL

        return super().url(name, parameters=parameters, expire=expire, http_method=http_method)