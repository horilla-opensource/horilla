"""
email_backend.py

This module is used to write email backends
"""
from django.core.mail.backends.smtp import EmailBackend
from horilla import settings
from base.thread_local_middleware import _thread_locals


class ConfiguredEmailBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=None,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs
    ):
        from base.models import DynamicEmailConfiguration

        request = getattr(_thread_locals, "request", None)
        compay = None
        if request:
            compay = request.user.employee_get.get_company()
        configuration = DynamicEmailConfiguration.objects.filter(
            company_id=compay
        ).first()
        # Use default settings if configuration is not available
        host = configuration.host if configuration else host or settings.EMAIL_HOST
        port = configuration.port if configuration else port or settings.EMAIL_PORT
        username = (
            configuration.username
            if configuration
            else username or settings.EMAIL_HOST_USER
        )
        password = (
            configuration.password
            if configuration
            else password or settings.EMAIL_HOST_PASSWORD
        )
        use_tls = (
            configuration.use_tls
            if configuration
            else use_tls or settings.EMAIL_USE_TLS
        )
        fail_silently = (
            configuration.fail_silently
            if configuration
            else fail_silently or getattr(settings,"EMAIL_FAIL_SILENTLY",True)
        )
        use_ssl = (
            configuration.use_ssl
            if configuration
            else use_ssl or getattr(settings,"EMAIL_USE_SSL",None)
        )
        timeout = (
            configuration.timeout
            if configuration
            else timeout or getattr(settings,"EMAIL_TIMEOUT",None)
        )
        ssl_keyfile = (
            getattr(configuration, "ssl_keyfile", None)
            if configuration
            else ssl_keyfile or getattr(settings, "ssl_keyfile", None)
        )
        ssl_certfile = (
            getattr(configuration, "ssl_certfile", None)
            if configuration
            else ssl_keyfile or getattr(settings, "ssl_certfile", None)
        )
        super(ConfiguredEmailBackend, self).__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            fail_silently=fail_silently,
            use_ssl=use_ssl,
            timeout=timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs
        )


__all__ = ["ConfiguredEmailBackend"]
