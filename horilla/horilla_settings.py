from django.core.files.storage import FileSystemStorage

from horilla import settings
from horilla.horilla_apps import INSTALLED_APPS

"""
DB_INIT_PASSWORD: str

The password used for database setup and initialization. This password is a
48-character alphanumeric string generated using a UUID to ensure high entropy and security.
"""
DB_INIT_PASSWORD = "d3f6a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d"


HORILLA_DATE_FORMATS = {
    "DD/MM/YY": "%d/%m/%y",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MMMM D, YYYY": "%B %d, %Y",
    "DD MMMM, YYYY": "%d %B, %Y",
    "MMM. D, YYYY": "%b. %d, %Y",
    "D MMM. YYYY": "%d %b. %Y",
    "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
}

HORILLA_TIME_FORMATS = {
    "hh:mm A": "%I:%M %p",  # 12-hour format
    "HH:mm": "%H:%M",  # 24-hour format
    "HH:mm:ss.SSSSSS": "%H:%M:%S.%f",  # 24-hour format with seconds and microseconds
}


BIO_DEVICE_THREADS = {}

DYNAMIC_URL_PATTERNS = []

FILE_STORAGE = FileSystemStorage(location="csv_tmp/")

APP_URLS = [
    "base.urls",
    "employee.urls",
]

APPS = [
    "base",
    "recruitment",
    "employee",
    "leave",
    "pms",
    "onboarding",
    "asset",
    "attendance",
    "payroll",
    "auth",
    "offboarding",
    "horilla_documents",
    "helpdesk",
]
if settings.env("AWS_ACCESS_KEY_ID", default=None):
    AWS_ACCESS_KEY_ID = settings.env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = settings.env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = settings.env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = settings.env("AWS_S3_REGION_NAME")
    DEFAULT_FILE_STORAGE = settings.env("DEFAULT_FILE_STORAGE")
    AWS_S3_ADDRESSING_STYLE = settings.env("AWS_S3_ADDRESSING_STYLE")

    settings.AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
    settings.AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
    settings.AWS_STORAGE_BUCKET_NAME = AWS_STORAGE_BUCKET_NAME
    settings.AWS_S3_REGION_NAME = AWS_S3_REGION_NAME
    settings.DEFAULT_FILE_STORAGE = DEFAULT_FILE_STORAGE
    settings.AWS_S3_ADDRESSING_STYLE = AWS_S3_ADDRESSING_STYLE


if settings.env("AWS_ACCESS_KEY_ID", default=None) and "storages" in INSTALLED_APPS:
    settings.MEDIA_URL = f"{settings.env('MEDIA_URL')}/{settings.env('NAMESPACE')}/"
    settings.MEDIA_ROOT = f"{settings.env('MEDIA_ROOT')}/{settings.env('NAMESPACE')}/"
