from django.core.files.storage import FileSystemStorage

from horilla import settings
from horilla.horilla_apps import INSTALLED_APPS

"""
DB_INIT_PASSWORD: str

The password used for database setup and initialization. This password is a
48-character alphanumeric string generated using a UUID to ensure high entropy and security.
"""
DB_INIT_PASSWORD = settings.env(
    "DB_INIT_PASSWORD", default="d3f6a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d"
)


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
    "employee",
    "horilla_documents",
    "horilla_automations",
]

NO_PERMISSION_MODALS = [
    "historicalbonuspoint",
    "assetreport",
    "assetdocuments",
    "returnimages",
    "holiday",
    "companyleave",
    "historicalavailableleave",
    "historicalleaverequest",
    "historicalleaveallocationrequest",
    "leaverequestconditionapproval",
    "historicalcompensatoryleaverequest",
    "employeepastleaverestrict",
    "overrideleaverequests",
    "historicalrotatingworktypeassign",
    "employeeshiftday",
    "historicalrotatingshiftassign",
    "historicalworktyperequest",
    "historicalshiftrequest",
    "multipleapprovalmanagers",
    "attachment",
    "announcementview",
    "emaillog",
    "driverviewed",
    "dashboardemployeecharts",
    "attendanceallowedip",
    "tracklatecomeearlyout",
    "historicalcontract",
    "overrideattendance",
    "overrideleaverequest",
    "overrideworkinfo",
    "multiplecondition",
    "historicalpayslip",
    "reimbursementmultipleattachment",
    "historicalcontract",
    "overrideattendance",
    "overrideleaverequest",
    "workrecord",
    "historicalticket",
    "skill",
    "historicalcandidate",
    "rejectreason",
    "historicalrejectedcandidate",
    "rejectedcandidate",
    "stagefiles",
    "stagenote",
    "questionordering",
    "recruitmentsurveyordering",
    "recruitmentsurveyanswer",
    "recruitmentgeneralsetting",
    "resume",
    "recruitmentmailtemplate",
]

if settings.env("AWS_ACCESS_KEY_ID", default=None):
    AWS_ACCESS_KEY_ID = settings.env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = settings.env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = settings.env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = settings.env("AWS_S3_REGION_NAME")
    DEFAULT_FILE_STORAGE = settings.env("DEFAULT_FILE_STORAGE")
    AWS_S3_ADDRESSING_STYLE = settings.env("AWS_S3_ADDRESSING_STYLE")
    AWS_S3_ENDPOINT_URL = settings.env("AWS_S3_ENDPOINT_URL", default=None)

    settings.AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
    settings.AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
    settings.AWS_STORAGE_BUCKET_NAME = AWS_STORAGE_BUCKET_NAME
    settings.AWS_S3_REGION_NAME = AWS_S3_REGION_NAME
    settings.DEFAULT_FILE_STORAGE = DEFAULT_FILE_STORAGE
    settings.AWS_S3_ADDRESSING_STYLE = AWS_S3_ADDRESSING_STYLE
    settings.AWS_S3_ENDPOINT_URL = AWS_S3_ENDPOINT_URL


if settings.env("AWS_ACCESS_KEY_ID", default=None) and "storages" in INSTALLED_APPS:
    settings.MEDIA_URL = f"{settings.env('MEDIA_URL')}/{settings.env('NAMESPACE')}/"
    settings.MEDIA_ROOT = f"{settings.env('MEDIA_ROOT')}/{settings.env('NAMESPACE')}/"


# Default LDAP settings
DEFAULT_LDAP_CONFIG = {
    "LDAP_SERVER": settings.env("LDAP_SERVER", default="ldap://127.0.0.1:389"),
    "BIND_DN": settings.env("BIND_DN", default="cn=admin,dc=horilla,dc=com"),
    "BIND_PASSWORD": settings.env("BIND_PASSWORD", default="horilla"),
    "BASE_DN": settings.env("BASE_DN", default="ou=users,dc=horilla,dc=com"),
}


def load_ldap_settings():
    """
    Fetch LDAP settings dynamically from the database after Django is ready.
    """
    try:
        from django.db import connection

        from horilla_ldap.models import LDAPSettings

        # Ensure DB is ready before querying
        if not connection.introspection.table_names():
            print("⚠️ Database is empty. Using default LDAP settings.")
            return DEFAULT_LDAP_CONFIG

        ldap_config = LDAPSettings.objects.first()
        if ldap_config:
            return {
                "LDAP_SERVER": ldap_config.ldap_server,
                "BIND_DN": ldap_config.bind_dn,
                "BIND_PASSWORD": ldap_config.bind_password,
                "BASE_DN": ldap_config.base_dn,
            }
    except Exception as e:
        print(f"⚠️ Warning: Could not load LDAP settings ({e})")
        return DEFAULT_LDAP_CONFIG  # Return default on error

    return DEFAULT_LDAP_CONFIG  # Fallback in case of an issue
