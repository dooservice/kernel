from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from fastapi import APIRouter, FastAPI

from .events import Events, Handler


class Listener(Protocol):
    """A background consumer owned by a module: a subscription, a periodic sweep."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class Module:
    """Contract every feature module fulfils. The kernel pulls contributions at boot;
    it never imports a module directly."""

    name: str = ""
    routers: Sequence[APIRouter] = ()
    root_routers: Sequence[APIRouter] = ()
    orm_model_modules: Sequence[str] = ()
    config_sections: Sequence[type] = ()

    def listeners(self, app: FastAPI) -> Sequence[Listener]:
        return ()

    async def on_startup(self, app: FastAPI) -> None:
        return None

    def subscriptions(self) -> Mapping[type, Handler]:
        """The events this module acts on, each with its handler."""
        return {}


class ModuleRegistry:
    def __init__(self, modules: Sequence[Module]) -> None:
        self.modules = tuple(modules)

    def orm_model_modules(self) -> list[str]:
        collected: list[str] = []
        for module in self.modules:
            collected.extend(module.orm_model_modules)
        return collected

    def config_sections(self) -> list[type]:
        """The struct of every configuration section the modules read, once each."""
        return list(dict.fromkeys(kind for module in self.modules for kind in module.config_sections))

    def routers(self) -> list[APIRouter]:
        return [router for module in self.modules for router in module.routers]

    def root_routers(self) -> list[APIRouter]:
        return [router for module in self.modules for router in module.root_routers]

    def listeners(self, app: FastAPI) -> list[Listener]:
        return [listener for module in self.modules for listener in module.listeners(app)]

    async def run_startup(self, app: FastAPI) -> None:
        for module in self.modules:
            await module.on_startup(app)

    def events(self) -> Events:
        handlers: dict[type, list[tuple[str, Handler]]] = {}
        for module in self.modules:
            for kind, handler in module.subscriptions().items():
                handlers.setdefault(kind, []).append((module.name, handler))
        return Events(handlers)
