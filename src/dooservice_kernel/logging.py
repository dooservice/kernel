from __future__ import annotations

import logging

from .http import job_id_var, request_id_var

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


class ContextInjectionFilter(logging.Filter):
    """Injects the current request/job correlation ids into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.job_id = job_id_var.get()
        return True


class LoggingSetup:
    @classmethod
    def configure(cls, debug: bool) -> None:
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format=LOG_FORMAT)
        for handler in logging.getLogger().handlers:
            handler.addFilter(ContextInjectionFilter())
