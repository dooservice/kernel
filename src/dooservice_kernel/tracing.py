"""OpenTelemetry traces, as an extension: `ApplicationBuilder(extensions=[Tracing()])`,
with the `tracing` extra installed.

Every request becomes a span. Where spans go is OpenTelemetry's own configuration, the
`OTEL_*` variables and whichever exporter the application installs; without one they
go nowhere and cost almost nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .health import Boundary


class Tracing:
    def install(self, app: FastAPI, boundaries: Sequence[Boundary]) -> None:
        FastAPIInstrumentor.instrument_app(app)
