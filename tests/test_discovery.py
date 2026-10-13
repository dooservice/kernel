from __future__ import annotations

from importlib.metadata import EntryPoint

import pytest

from dooservice_kernel import discovery
from dooservice_kernel.discovery import ModuleDiscovery, ModuleSelection, UnknownModulesError
from dooservice_kernel.registry import Module
from dooservice_kernel.sections import ModulesConfig


class Shop(Module):
    name = "shop"


class Ledger(Module):
    name = "ledger"


def names(modules: list[Module]) -> list[str]:
    return [module.name for module in modules]


def test_every_module_runs_unless_the_configuration_says_otherwise() -> None:
    assert names(ModuleSelection(ModulesConfig()).apply([Shop(), Ledger()])) == ["shop", "ledger"]
    assert names(ModuleSelection(ModulesConfig(enabled=["ledger"])).apply([Shop(), Ledger()])) == ["ledger"]
    assert names(ModuleSelection(ModulesConfig(disabled=["shop"])).apply([Shop(), Ledger()])) == ["ledger"]


def test_a_name_that_matches_no_module_is_refused() -> None:
    with pytest.raises(UnknownModulesError, match="shopp"):
        ModuleSelection(ModulesConfig(disabled=["shopp"])).apply([Shop()])


def test_installed_packages_offer_their_modules_by_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    offered = [EntryPoint(name="shop", value=f"{__name__}:Shop", group=discovery.ENTRY_POINTS)]
    monkeypatch.setattr(discovery, "entry_points", lambda group: offered if group == discovery.ENTRY_POINTS else [])

    assert names(ModuleDiscovery().installed()) == ["shop"]
