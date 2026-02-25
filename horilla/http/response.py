from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages


class HorillaRedirect(HttpResponseRedirect):
    """
    Safe redirect class to prevent open redirect vulnerabilities.
    Validates the target URL before redirecting.
    """

    def __init__(self, request, redirect_to=None, message=None, fallback_url="/"):
        """
        :param request: Django request object
        :param redirect_to: Target URL (optional)
        :param fallback_url: Safe fallback if URL is unsafe
        """

        # If redirect_to not provided, use HTTP_REFERER
        previous_url = redirect_to or request.META.get("HTTP_REFERER", fallback_url)

        if message:
            messages.error(request, message)

        # Validate URL safety
        if not url_has_allowed_host_and_scheme(
            previous_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            previous_url = fallback_url

        if request.headers.get("HX-Request"):
            super().__init__(previous_url)
            self.status_code = 200
            self.headers.pop("Location", None)
            self.headers["HX-Redirect"] = previous_url
        else:
            super().__init__(previous_url)
