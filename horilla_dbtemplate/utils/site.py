"""
Site resolution for template loading.

Resolves the effective Site only when the request host matches a Site domain.
If the host does not match any Site (e.g. localhost when only devtunnels.ms
is configured), we return None so the loader uses only global templates and
filesystem — avoiding get_current() so localhost does not get another site's
templates.

When the app is behind a reverse proxy (e.g. devtunnels, nginx), the proxy often
forwards to Django on localhost and may set the original host in X-Forwarded-Host.
We use that header when present so site resolution sees the public host, not
localhost.
"""

# Third-party imports (Django)
from django.contrib.sites.models import Site


def get_request_host(request):
    """
    Return the host to use for site resolution, proxy-aware.

    When behind a reverse proxy (devtunnels, nginx, etc.), the request may have
    Host=localhost:80 while the real host is in X-Forwarded-Host. We prefer
    X-Forwarded-Host (and optionally X-Forwarded-Port) so template resolution
    uses the public domain (e.g. 46sqfhkb-80.inc1.devtunnels.ms).
    """
    if not request:
        return None
    # Prefer forwarded host when behind a proxy (devtunnels, nginx, load balancer)
    forwarded_host = request.META.get("HTTP_X_FORWARDED_HOST")
    if forwarded_host:
        # Can be "host" or "host1, host2" (first is the client-facing one)
        host = forwarded_host.split(",")[0].strip()
        forwarded_port = request.META.get("HTTP_X_FORWARDED_PORT")
        if forwarded_port and ":" not in host:
            host = f"{host}:{forwarded_port}"
        return host
    return request.get_host()


def get_site_for_request(request):
    """
    Return the Site for the current request only when host matches a Site domain.

    - Uses proxy-aware host (X-Forwarded-Host when behind reverse proxy).
    - If that host matches a Site domain, return that Site.
    - Otherwise return None (do not use get_current()).
    """
    site = None
    if request:
        host = get_request_host(request)
        # Try exact match first (e.g. "46sqfhkb-80.inc1.devtunnels.ms" or "localhost:8000")
        site = Site.objects.filter(domain__iexact=host).first()
        if site is None and host and ":" in host:
            # Try without port (e.g. "localhost" for "localhost:8000")
            site = Site.objects.filter(domain__iexact=host.split(":")[0]).first()
    return site
