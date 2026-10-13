"""Modules installed as packages, and which of all the modules run.

A package offers its modules under the `dooservice_kernel.modules` entry point group,
each naming a `Module` subclass:

    [project.entry-points."dooservice_kernel.modules"]
    shop = "shop.module:ShopModule"

`[modules]` in the configuration then picks: `enabled` lists the only ones that run when
it is not empty, `disabled` takes some out, and a name that matches no module is refused
so a typo does not quietly turn a module off.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import entry_points

from .registry import Module
from .sections import ModulesConfig

ENTRY_POINTS = "dooservice_kernel.modules"


class UnknownModulesError(ValueError):
    def __init__(self, names: set[str]) -> None:
        super().__init__(f"[modules] names modules that do not exist: {', '.join(sorted(names))}")


class ModuleDiscovery:
    def __init__(self, group: str = ENTRY_POINTS) -> None:
        self.group = group

    def installed(self) -> list[Module]:
        """A fresh instance of every module installed packages offer, by entry point name."""
        found = sorted(entry_points(group=self.group), key=lambda point: point.name)
        return [point.load()() for point in found]


class ModuleSelection:
    def __init__(self, chosen: ModulesConfig) -> None:
        self.chosen = chosen

    def apply(self, modules: Sequence[Module]) -> list[Module]:
        names = {module.name for module in modules}
        unknown = (set(self.chosen.enabled) | set(self.chosen.disabled)) - names
        if unknown:
            raise UnknownModulesError(unknown)
        kept = [module for module in modules if not self.chosen.enabled or module.name in self.chosen.enabled]
        return [module for module in kept if module.name not in self.chosen.disabled]
