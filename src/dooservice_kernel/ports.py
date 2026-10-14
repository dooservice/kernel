"""What one module offers others, found by its type instead of by a name on `app.state`.

A module lists the ports it `provides` and those it `requires`; the registry boots the
providers first and refuses to start when a requirement has no provider. In
`on_startup` the provider registers its implementation and the others ask for it by type:

    app.state.ports.provide(PlanLimits, StripePlanLimits())
    limits = app.state.ports.get(PlanLimits)

A `default` implementation may be replaced by the one a later module provides; two
providers of the same port that are not defaults are a mistake, and refused.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, cast

T = TypeVar("T")


class HasState(Protocol):
    """An application, or anything that carries one's `state`: FastAPI, Starlette."""

    @property
    def state(self) -> Any: ...


class MissingPortError(LookupError):
    def __init__(self, kind: type, who: str = "") -> None:
        needed = f" (required by {who})" if who else ""
        super().__init__(f"nothing provides {kind.__name__}{needed}")


class PortTakenError(ValueError):
    def __init__(self, kind: type) -> None:
        super().__init__(f"{kind.__name__} is provided twice")


class Ports:
    def __init__(self) -> None:
        self.found: dict[type, object] = {}
        self.defaults: set[type] = set()

    def provide(self, kind: type[T], implementation: T, default: bool = False) -> None:
        if kind in self.found and kind not in self.defaults and not default:
            raise PortTakenError(kind)
        if kind in self.found and default:
            return
        self.found[kind] = implementation
        if default:
            self.defaults.add(kind)
        else:
            self.defaults.discard(kind)

    def get(self, kind: type[T]) -> T:
        if kind not in self.found:
            raise MissingPortError(kind)
        return cast("T", self.found[kind])

    def has(self, kind: type) -> bool:
        return kind in self.found

    def replace(self, kind: type[T], implementation: T) -> None:
        """Put another implementation where one was provided: how a test stands a fake in.

        Only what was provided can be replaced, so a test cannot make up a port the
        application never offers.
        """
        if kind not in self.found:
            raise MissingPortError(kind)
        self.found[kind] = implementation

    @staticmethod
    def of(app: HasState) -> Ports:
        """The ports of an application, with their type, from the app or a request's `app`."""
        ports = app.state.ports
        if not isinstance(ports, Ports):
            raise TypeError("app.state.ports is not the kernel's Ports")
        return ports
