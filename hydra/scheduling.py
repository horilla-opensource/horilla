import sys

from django.conf import settings


MANAGEMENT_COMMANDS_WITHOUT_SCHEDULERS = {
    "check",
    "collectstatic",
    "compilemessages",
    "flush",
    "hydra_readiness",
    "makemigrations",
    "migrate",
    "shell",
    "test",
}


def should_start_schedulers(argv=None):
    """Return whether this process may own legacy in-process schedulers."""

    arguments = set(sys.argv if argv is None else argv)
    return not getattr(settings, "HYDRA_DISABLE_SCHEDULERS", False) and not (
        arguments & MANAGEMENT_COMMANDS_WITHOUT_SCHEDULERS
    )
