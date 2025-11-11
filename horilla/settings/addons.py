from .local_settings import *

if env("AWS_ACCESS_KEY_ID", default=None):
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME")
    DEFAULT_FILE_STORAGE = env("DEFAULT_FILE_STORAGE")
    AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE")

if env("AWS_ACCESS_KEY_ID", default=None) and "storages" not in INSTALLED_APPS:
    INSTALLED_APPS.append("storages")

if env("AWS_ACCESS_KEY_ID", default=None) and "storages" in INSTALLED_APPS:
    MEDIA_URL = f"{env('MEDIA_URL')}/{env('NAMESPACE')}/"
    MEDIA_ROOT = f"{env('MEDIA_ROOT')}/{env('NAMESPACE')}/"
