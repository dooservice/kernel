"""The application's command line: its own commands, each module's under its name, and
`check-config`, which reads the configuration file the way the service would and stops.

    shop check-config
    shop ledger rebuild --since 2026-01-01
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import cyclopts

from .config import Config
from .registry import Module


class CommandLine:
    def __init__(self, name: str, modules: Sequence[Module], load_config: Callable[[], Config]) -> None:
        self.load_config = load_config
        self.app = cyclopts.App(name=name)
        self.app.command(self.check_config)
        for module in modules:
            commands = module.commands()
            if not commands:
                continue
            group = cyclopts.App(name=module.name, help=f"Commands of the {module.name} module.")
            for command in commands:
                group.command(command)
            self.app.command(group)

    def check_config(self) -> None:
        """Read the configuration file and every module's section, and say whether it holds."""
        config = self.load_config()
        sections = sorted(type(section).__name__ for section in config.sections.values())
        print(f"The configuration holds: the kernel's sections and {len(sections)} of the modules'.")
        for name in sections:
            print(f"  {name}")

    def __call__(self, tokens: Sequence[str] | None = None) -> None:
        """Run as a program: the command's outcome becomes the exit code."""
        self.app(tokens)

    def run(self, tokens: Sequence[str]) -> object:
        """Run one command and hand back what it returned, as a test does."""
        return self.app(tokens, result_action="return_value")
