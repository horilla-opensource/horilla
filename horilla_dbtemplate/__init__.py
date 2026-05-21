"""
horilla_dbtemplate - Database-backed template loader with host/domain-based resolution.

Resolution order:
1. Template matching current request host domain (only when host matches a Site)
2. Global template (sites__isnull=True)
3. Fall back to filesystem/app_directories loaders

When host (e.g. localhost) does not match any Site, only global and filesystem
templates are used — get_current() is not used, so localhost does not receive
templates assigned only to another domain.
"""
