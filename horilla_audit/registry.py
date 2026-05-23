"""
registry.py

Manages dynamic registration of models with the django-auditlog registry
based on ``AuditModelConfig`` rows. When the config table is empty the
default set of Employee-related models is tracked.
"""

import logging

from auditlog.registry import auditlog
from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


DEFAULT_TRACKED_MODELS = [
    ("employee", "Employee"),
    ("employee", "EmployeeWorkInformation"),
    ("employee", "EmployeeBankDetails"),
]

# Models registered by this module so we can safely unregister them later
# without touching registrations made elsewhere.
_managed_registrations: set = set()


def _resolve_model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        logger.debug("Audit registry: model %s.%s not found", app_label, model_name)
        return None


def _register(model, fields):
    """Register ``model`` with auditlog using optional include_fields."""
    kwargs = {"serialize_data": True}
    if fields:
        kwargs["include_fields"] = list(fields)
    try:
        # auditlog.register no-ops silently if already registered, but we
        # unregister first to allow field-set updates to take effect.
        if auditlog.contains(model):
            auditlog.unregister(model)
        auditlog.register(model, **kwargs)
        _managed_registrations.add(model)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Audit registry: failed to register %s", model)


def _unregister(model):
    try:
        if auditlog.contains(model):
            auditlog.unregister(model)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Audit registry: failed to unregister %s", model)
    _managed_registrations.discard(model)


def _load_targets():
    """
    Return a list of ``(model_class, fields)`` tuples to register.
    Falls back to ``DEFAULT_TRACKED_MODELS`` when the config table is
    empty or unavailable (e.g. before migrations run).
    """
    targets = []
    try:
        from horilla_audit.models import AuditModelConfig

        configs = list(AuditModelConfig.objects.filter(is_enabled=True))
    except (OperationalError, ProgrammingError, Exception):
        configs = []

    if configs:
        for cfg in configs:
            model = _resolve_model(cfg.app_label, cfg.model_name)
            if model:
                targets.append((model, cfg.tracked_fields or []))
        return targets

    for app_label, model_name in DEFAULT_TRACKED_MODELS:
        model = _resolve_model(app_label, model_name)
        if model:
            targets.append((model, []))
    return targets


def apply_audit_configuration():
    """
    Synchronise the auditlog registry with the desired configuration.
    Safe to call multiple times.
    """
    desired = _load_targets()
    desired_models = {m for m, _ in desired}

    # Unregister anything we previously managed but no longer want.
    for model in list(_managed_registrations):
        if model not in desired_models:
            _unregister(model)

    for model, fields in desired:
        _register(model, fields)


def on_config_change(sender, instance=None, **kwargs):
    """Signal handler that reapplies configuration after a row changes."""
    apply_audit_configuration()
