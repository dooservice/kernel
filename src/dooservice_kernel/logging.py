"""Every log line carries the request id, and the job id when there is one; as text for
a person reading a terminal, or as one JSON object per line for whatever collects logs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging

from .http import job_id_var, request_id_var

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


class ContextInjectionFilter(logging.Filter):
    """Injects the current request/job correlation ids into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.job_id = job_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "job_id": getattr(record, "job_id", "-"),
        }
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False)


class LoggingSetup:
    @classmethod
    def configure(cls, debug: bool, as_json: bool = False) -> None:
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format=LOG_FORMAT)
        for handler in logging.getLogger().handlers:
            handler.addFilter(ContextInjectionFilter())
            if as_json:
                handler.setFormatter(JsonFormatter())
