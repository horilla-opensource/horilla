SECURE_COOKIE_NAMES = frozenset(("hydra_csrftoken", "hydra_sessionid"))


def prepare_internal_http_cookies(cookie_jar):
    """Allow staging Secure cookies only on the private HTTP proxy hop."""

    for cookie in cookie_jar:
        if cookie.name in SECURE_COOKIE_NAMES:
            cookie.secure = False
