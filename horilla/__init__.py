"""
init.py
"""

import sys

# Patch makemigrations and migrate to use HorillaAutodetector.
#
# Django stores the autodetector as a class attribute on each command
# (`autodetector = MigrationAutodetector`), so we patch the class attribute
# directly — patching the module-level name has no effect.
#
# Django 6.x requires both commands to share the same autodetector class
# (system check commands.E001), so we always patch both.
try:
    from django.core.management.commands.makemigrations import Command as _MM
    from django.core.management.commands.migrate import Command as _Migrate

    from horilla.inherit.autodetect import HorillaAutodetector

    _MM.autodetector = HorillaAutodetector
    _Migrate.autodetector = HorillaAutodetector
except ImportError:
    pass
