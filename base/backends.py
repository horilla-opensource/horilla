"""
email_backend.py

This module is used to write email backends
"""

import importlib

from django.core.mail.backends.smtp import EmailBackend

from base.models import DynamicEmailConfiguration, EmailLog
from base.thread_local_middleware import _thread_locals
from horilla import settings


class DefaultHorillaMailBackend(EmailBackend):
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
        **kwargs,
    ):
        self.configuration = self.get_dynamic_email_config()
        ssl_keyfile = (
            getattr(self.configuration, "ssl_keyfile", None)
            if self.configuration
            else ssl_keyfile or getattr(settings, "ssl_keyfile", None)
        )
        ssl_certfile = (
            getattr(self.configuration, "ssl_certfile", None)
            if self.configuration
            else ssl_keyfile or getattr(settings, "ssl_certfile", None)
        )
        self.mail_sent_from = self.dynamic_username
        super().__init__(
            host=self.dynamic_host,
            port=self.dynamic_port,
            username=self.dynamic_username,
            password=self.dynamic_password,
            use_tls=self.dynamic_use_tls,
            fail_silently=self.dynamic_fail_silently,
            use_ssl=self.dynamic_use_ssl,
            timeout=self.dynamic_timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs,
        )

    @staticmethod
    def get_dynamic_email_config():
        request = getattr(_thread_locals, "request", None)
        company = None
        if request and not request.user.is_anonymous:
            company = request.user.employee_get.get_company()
        configuration = DynamicEmailConfiguration.objects.filter(
            company_id=company
        ).first()
        if configuration is None:
            configuration = DynamicEmailConfiguration.objects.filter(
                is_primary=True
            ).first()
        return configuration

    @property
    def dynamic_host(self):
        return (
            self.configuration.host
            if self.configuration
            else getattr(settings, "EMAIL_HOST", None)
        )

    @property
    def dynamic_port(self):
        return (
            self.configuration.port
            if self.configuration
            else getattr(settings, "EMAIL_PORT", None)
        )

    @property
    def dynamic_username(self):
        return (
            self.configuration.username
            if self.configuration
            else getattr(settings, "EMAIL_HOST_USER", None)
        )

    @property
    def dynamic_display_name(self):
        return self.configuration.display_name if self.configuration else None

    @property
    def dynamic_username_with_display_name(self):
        return (
            f"{self.dynamic_display_name} <{self.dynamic_username}>"
            if self.dynamic_display_name
            else self.dynamic_username
        )

    @property
    def dynamic_password(self):
        return (
            self.configuration.password
            if self.configuration
            else getattr(settings, "EMAIL_HOST_PASSWORD", None)
        )

    @property
    def dynamic_use_tls(self):
        return (
            self.configuration.use_tls
            if self.configuration
            else getattr(settings, "EMAIL_USE_TLS", None)
        )

    @property
    def dynamic_fail_silently(self):
        return (
            self.configuration.fail_silently
            if self.configuration
            else getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        )

    @property
    def dynamic_use_ssl(self):
        return (
            self.configuration.use_ssl
            if self.configuration
            else getattr(settings, "EMAIL_USE_SSL", None)
        )

    @property
    def dynamic_timeout(self):
        return (
            self.configuration.timeout
            if self.configuration
            else getattr(settings, "EMAIL_TIMEOUT", None)
        )


EMAIL_BACKEND = getattr(settings, "EMAIL_BACKEND", "")


BACKEND_CLASS: EmailBackend = DefaultHorillaMailBackend
default = "base.backends.ConfiguredEmailBackend"

setattr(BACKEND_CLASS, "send_messages", DefaultHorillaMailBackend.send_messages)

if EMAIL_BACKEND and EMAIL_BACKEND != default:
    module_path, class_name = EMAIL_BACKEND.rsplit(".", 1)
    module = importlib.import_module(module_path)
    BACKEND_CLASS = getattr(module, class_name)


class ConfiguredEmailBackend(BACKEND_CLASS):

    def send_messages(self, email_messages):
        response = super(BACKEND_CLASS, self).send_messages(email_messages)
        for message in email_messages:
            email_log = EmailLog(
                subject=message.subject,
                from_email=self.mail_sent_from,
                to=message.to,
                body=message.body,
                status="sent" if response else "failed",
            )
            email_log.save()
        return response


if EMAIL_BACKEND != default:
    from_mail = getattr(settings, "EMAIL_HOST_USER", "example@gmail.com")
    ConfiguredEmailBackend.dynamic_username = from_mail
    ConfiguredEmailBackend.dynamic_username_with_display_name = from_mail


__all__ = ["ConfiguredEmailBackend"]
