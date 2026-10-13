"""What an application adds to the app the kernel builds, beyond its modules: metrics,
traces, a middleware of its own. The application imports the extension and passes it to
`ApplicationBuilder(extensions=[...])`, so an optional dependency is imported only by
whoever uses it, and always at the top of a file."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from fastapi import FastAPI

from .health import Boundary


class Extension(Protocol):
    def install(self, app: FastAPI, boundaries: Sequence[Boundary]) -> None: ...
