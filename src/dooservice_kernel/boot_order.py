"""The order modules boot in: as the application lists them, except that a module boots
after every module that provides a port it requires."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from .ports import MissingPortError

if TYPE_CHECKING:
    from .registry import Module


class DependencyCycleError(ValueError):
    def __init__(self, names: Sequence[str]) -> None:
        super().__init__(f"these modules require each other's ports: {', '.join(names)}")


class BootOrder:
    def __init__(self, modules: Sequence[Module]) -> None:
        self.modules = list(modules)

    def providers(self) -> dict[type, list[int]]:
        found: dict[type, list[int]] = {}
        for index, module in enumerate(self.modules):
            for kind in module.provides:
                found.setdefault(kind, []).append(index)
        return found

    def resolve(self) -> list[Module]:
        providers = self.providers()
        after: dict[int, set[int]] = {}
        for index, module in enumerate(self.modules):
            needs: set[int] = set()
            for kind in module.requires:
                if kind not in providers:
                    raise MissingPortError(kind, module.name)
                needs |= {provider for provider in providers[kind] if provider != index}
            after[index] = needs
        placed: list[int] = []
        while len(placed) < len(self.modules):
            ready = [index for index in range(len(self.modules)) if index not in placed and after[index] <= set(placed)]
            if not ready:
                raise DependencyCycleError([self.modules[i].name for i in range(len(self.modules)) if i not in placed])
            placed.append(ready[0])
        return [self.modules[index] for index in placed]
