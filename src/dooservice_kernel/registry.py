from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Protocol

from fastapi import APIRouter, FastAPI

from .boot_order import BootOrder
from .events import EventBridge, Events, Handler
from .ports import MissingPortError, Ports


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
    provides: Sequence[type] = ()
    requires: Sequence[type] = ()

    def listeners(self, app: FastAPI) -> Sequence[Listener]:
        return ()

    async def on_startup(self, app: FastAPI) -> None:
        return None

    def subscriptions(self) -> Mapping[type, Handler]:
        """The events this module acts on, each with its handler."""
        return {}

    def health_checks(self) -> Mapping[str, Callable[[], Awaitable[bool]]]:
        """What `/health/ready` asks of this module besides the database and the boundaries,
        each by a name; a check that raises counts as failing."""
        return {}

    def commands(self) -> Sequence[Callable[..., Any]]:
        """The commands it adds to the application's command line, under its name."""
        return ()


class ModuleRegistry:
    def __init__(self, modules: Sequence[Module]) -> None:
        self.modules = tuple(BootOrder(modules).resolve())

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
        """Each module's startup, then a check that every port a module requires was
        provided by the one that said it would."""
        for module in self.modules:
            await module.on_startup(app)
        ports: Ports = app.state.ports
        for module in self.modules:
            for kind in module.requires:
                if not ports.has(kind):
                    raise MissingPortError(kind, module.name)

    def events(self, bridge: EventBridge | None = None) -> Events:
        handlers: dict[type, list[tuple[str, Handler]]] = {}
        for module in self.modules:
            for kind, handler in module.subscriptions().items():
                handlers.setdefault(kind, []).append((module.name, handler))
        return Events(handlers, bridge)

    def health_checks(self) -> dict[str, Callable[[], Awaitable[bool]]]:
        """Every module's checks, named `<module>.<check>`."""
        return {
            f"{module.name}.{name}": check
            for module in self.modules
            for name, check in module.health_checks().items()
        }
