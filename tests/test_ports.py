from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI
import pytest

from dooservice_kernel.boot_order import DependencyCycleError
from dooservice_kernel.ports import MissingPortError, Ports, PortTakenError
from dooservice_kernel.registry import Module, ModuleRegistry


class PlanLimits(Protocol):
    def projects(self) -> int: ...


class Free:
    def projects(self) -> int:
        return 1


class Paid:
    def projects(self) -> int:
        return 10


class Billing(Module):
    name = "billing"
    provides = (PlanLimits,)

    async def on_startup(self, app: FastAPI) -> None:
        app.state.ports.provide(PlanLimits, Paid())


class Projects(Module):
    name = "projects"
    requires = (PlanLimits,)


def test_a_module_boots_after_the_one_that_provides_what_it_requires() -> None:
    registry = ModuleRegistry([Projects(), Billing()])

    assert [module.name for module in registry.modules] == ["billing", "projects"]


def test_a_requirement_nobody_provides_stops_the_boot() -> None:
    with pytest.raises(MissingPortError, match="PlanLimits"):
        ModuleRegistry([Projects()])


def test_two_modules_requiring_each_other_are_refused() -> None:
    class A(Module):
        name = "a"
        provides = (int,)
        requires = (str,)

    class B(Module):
        name = "b"
        provides = (str,)
        requires = (int,)

    with pytest.raises(DependencyCycleError):
        ModuleRegistry([A(), B()])


async def test_a_provider_that_did_not_register_its_port_is_found_at_startup() -> None:
    class Forgetful(Billing):
        async def on_startup(self, app: FastAPI) -> None:
            return None

    app = FastAPI()
    app.state.ports = Ports()
    with pytest.raises(MissingPortError):
        await ModuleRegistry([Projects(), Forgetful()]).run_startup(app)


def test_a_default_gives_way_to_the_real_one_and_two_real_ones_are_refused() -> None:
    ports = Ports()
    ports.provide(PlanLimits, Free(), default=True)
    ports.provide(PlanLimits, Paid())
    ports.provide(PlanLimits, Free(), default=True)

    assert ports.get(PlanLimits).projects() == 10
    with pytest.raises(PortTakenError):
        ports.provide(PlanLimits, Paid())
