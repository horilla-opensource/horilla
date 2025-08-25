"""
horilla/backends.py
"""

import ssl

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

# import certifi
from base.models import EmailLog


class CustomSSLContext(ssl.SSLContext):
    """
    CustomSSLContext
    """

    def __init__(self):
        super().__init__()
        # self.load_verify_locations(cafile=certifi.where())


class ZimbraBackend(SMTPBackend):
    """
    ZimbraBackend Class
    """

    def __init__(self, *args, **kwargs):
        # Initialize the parent SMTP backend
        super().__init__(*args, **kwargs)
        self.ssl_context = CustomSSLContext()

    def open(self):
        """Establish the SMTP connection using the custom SSL context and TLS."""
        if self.connection:
            return False  # Connection already open

        try:
            # Create the SMTP connection with the custom SSL context
            self.connection = self.connection_class(
                host=self.host, port=self.port, timeout=self.timeout
            )

            if self.use_tls:
                # Start TLS with custom SSL context
                self.connection.starttls(context=self.ssl_context)
                print(f"Started TLS on {self.host}:{self.port}")

            # Authenticate after starting TLS
            self.connection.login(self.username, self.password)
            print(
                f"Successfully connected and authenticated on {self.host}:{self.port}"
            )

        except Exception as e:
            print(f"Failed to connect or authenticate: {e}")
            self.close()
            return False
        return True

    def send_messages(self, email_messages):
        """Send messages and log the results to the database."""
        if not self.open():
            print("Failed to open connection.")
            return 0

        response = super().send_messages(email_messages)
        for message in email_messages:
            # Log each email to the EmailLog model
            email_log = EmailLog(
                subject=message.subject,
                from_email=message.from_email,
                to=message.to,
                body=message.body,
                status="sent" if response else "failed",
            )
            email_log.save()
        return response

    def close(self):
        """Ensure the SMTP connection is closed after use."""
        if self.connection:
            try:
                self.connection.quit()
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self.connection = None
