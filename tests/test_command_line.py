from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import pytest

from dooservice_kernel.command_line import CommandLine
from dooservice_kernel.config import Config
from dooservice_kernel.registry import Module


class Ledger(Module):
    name = "ledger"

    def __init__(self) -> None:
        self.rebuilt: list[str] = []

    def commands(self) -> Sequence[Callable[..., Any]]:
        return (self.rebuild,)

    def rebuild(self, since: str) -> None:
        """Rebuild the ledger from a date."""
        self.rebuilt.append(since)


def config() -> Config:
    return Config.read({"session": {"secret": "s"}}, [])


def test_a_module_command_runs_under_the_module_name() -> None:
    ledger = Ledger()
    command_line = CommandLine("shop", [ledger], config)

    command_line.run(["ledger", "rebuild", "--since", "2026-01-01"])

    assert ledger.rebuilt == ["2026-01-01"]


def test_check_config_reads_the_file_the_way_the_service_would(capsys: pytest.CaptureFixture[str]) -> None:
    CommandLine("shop", [], config).run(["check-config"])

    assert "The configuration holds" in capsys.readouterr().out
