from contextvars import ContextVar
from logging import Filter


request_id_context = ContextVar("hydra_request_id", default="-")


class RequestIdFilter(Filter):
    """Make a request id available to log formatters without request data."""

    def filter(self, record):
        record.request_id = request_id_context.get()
        return True
