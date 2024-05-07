import os

from horilla import settings

setattr(
    settings,
    "HAYSTACK_CONNECTIONS",
    {
        "default": {
            "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
            "PATH": os.path.join(
                settings.BASE_DIR, "whoosh_index"
            ),  # Set the path to the Whoosh index
        },
    },
)

setattr(
    settings,
    "HAYSTACK_SIGNAL_PROCESSORS",
    {
        "helpdesk": "helpdesk.signals.SignalProcessor",
    },
)
