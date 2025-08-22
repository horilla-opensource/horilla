"""
horilla/horilla_backends.py
"""

from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    """
    PrivateMediaStorage
    """

    location = "private"
    default_acl = "private"
    file_overwrite = False
    custom_domain = False


models.FileField.storage = PrivateMediaStorage()
models.ImageField.storage = PrivateMediaStorage()
