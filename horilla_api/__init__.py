from horilla.settings import INSTALLED_APPS

INSTALLED_APPS.append("geofencing")
INSTALLED_APPS.append("facedetection")


# Import Swagger settings to ensure they're applied
from . import swagger_settings
