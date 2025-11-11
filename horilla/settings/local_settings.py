"""
Custom client-specific overrides.
This file is intentionally empty by default and should NOT be tracked by Git.
"""
from .base import *

# # --- 1️⃣ Basic overrides ---
# DEBUG = False
# ALLOWED_HOSTS = ["client.example.com"]
# WHITE_LABELLING = True
# TWO_FACTORS_AUTHENTICATION = True


# # --- 2️⃣ Add extra apps ---
# # Make sure to extend, not replace
# INSTALLED_APPS += [
#     "client_portal",
#     "client_analytics",
# ]


# # --- 3️⃣ Add custom middleware ---
# MIDDLEWARE += [
#     "client_portal.middleware.ClientTrackingMiddleware",
# ]


# # --- 4️⃣ Override any other settings if needed ---
# TIME_ZONE = "Europe/Berlin"
# LANGUAGE_CODE = "de"