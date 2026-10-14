import json

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme


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

        # Sec-Fetch-Mode is set by the browser itself for a genuine top-level
        # navigation and can't be spoofed by an htmx fetch() call, unlike the
        # HX-Request header alone -- some browser setups send HX-Request even
        # on a real address-bar visit, which would otherwise get the empty
        # HX-Redirect-header response below and render as a blank page,
        # since there's no htmx.js there to read that header.
        is_real_navigation = request.headers.get("Sec-Fetch-Mode") == "navigate"
        if request.headers.get("HX-Request") and not is_real_navigation:
            super().__init__(previous_url)
            self.status_code = 200
            self.headers.pop("Location", None)
            self.headers["HX-Redirect"] = previous_url
        else:
            super().__init__(previous_url)


def with_bulk_result(response, done, failed):
    """
    Report the outcome of a bulk approve / reject to the browser.

    static/index/index.js reads this header and shows a Total / Approved (or
    Rejected) / Failed dialog in place of the per-record toasts, which
    BulkDeleteSummaryMiddleware drops for any response carrying it.
    """
    response["X-Hlv-Bulk-Result"] = json.dumps({"done": done, "failed": failed})
    return response
