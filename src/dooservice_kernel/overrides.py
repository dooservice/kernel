"""Values of the configuration file replaced from the environment, and secrets read from
files, so that the same file serves every deployment and no secret has to live in it.

With the prefix `SHOP`:

    SHOP__SHOP__CURRENCY=PEN                       [shop] currency = "PEN"
    SHOP__SERVER__PORT=8080                        [server] port = 8080
    SHOP__SESSION__SECRET__FILE=/run/secrets/key   [session] secret = <the file's contents>

A value is read as TOML when it is one (`8080`, `true`, `["a", "b"]`) and as text
otherwise. A file's contents lose their trailing newline.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
from pathlib import Path
import tomllib
from typing import Any

SEPARATOR = "__"
FROM_FILE = "file"


class EnvironmentOverrides:
    def __init__(self, prefix: str, environ: Mapping[str, str]) -> None:
        self.prefix = f"{prefix}{SEPARATOR}" if prefix else ""
        self.environ = environ

    @staticmethod
    def value(raw: str) -> Any:
        try:
            return tomllib.loads(f"value = {raw}")["value"]
        except tomllib.TOMLDecodeError:
            return raw

    def overrides(self) -> list[tuple[list[str], Any]]:
        if not self.prefix:
            return []
        found = []
        for name, raw in sorted(self.environ.items()):
            if not name.startswith(self.prefix):
                continue
            path = [part.lower() for part in name[len(self.prefix) :].split(SEPARATOR)]
            if len(path) > 2 and path[-1] == FROM_FILE:
                found.append((path[:-1], Path(raw).read_text().rstrip("\n")))
            elif len(path) >= 2:
                found.append((path, self.value(raw)))
        return found

    def apply(self, data: Mapping[str, Any]) -> dict[str, Any]:
        merged = copy.deepcopy(dict(data))
        for path, value in self.overrides():
            table = merged
            for key in path[:-1]:
                table = table.setdefault(key, {})
            table[path[-1]] = value
        return merged
