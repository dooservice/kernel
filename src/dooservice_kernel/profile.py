"""What tells one application built on the kernel from another."""

from __future__ import annotations

import msgspec

from .migrations import Baseline


class Profile(msgspec.Struct, frozen=True):
    """Its name in the API docs, the prefix its modules' routes are mounted under, the
    cookie that carries the OAuth state, the package of its migrations, and the database
    it may have started from before it had migrations."""

    title: str = "application"
    api_prefix: str = "/api"
    state_cookie: str = "oauth_state"
    migrations: str = ""
    baseline: Baseline | None = None
