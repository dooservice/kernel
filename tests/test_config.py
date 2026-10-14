from __future__ import annotations

from typing import ClassVar

import msgspec
import pytest

from dooservice_kernel.config import Config, UnknownSectionsError


class ShopConfig(msgspec.Struct, forbid_unknown_fields=True):
    section: ClassVar[str] = "shop"

    currency: str = "USD"


def test_the_kernel_reads_its_sections_and_each_module_its_own() -> None:
    config = Config.read({"session": {"secret": "s"}, "shop": {"currency": "PEN"}}, [ShopConfig])

    assert config.session.secret == "s"
    assert config.server.port == 3000
    assert config.section(ShopConfig).currency == "PEN"


def test_a_section_missing_from_the_file_comes_with_its_defaults() -> None:
    config = Config.read({"session": {"secret": "s"}}, [ShopConfig])

    assert config.section(ShopConfig).currency == "USD"


def test_a_section_no_module_declares_is_refused() -> None:
    with pytest.raises(UnknownSectionsError, match="shp"):
        Config.read({"session": {"secret": "s"}, "shp": {}}, [ShopConfig])


def test_an_unknown_key_inside_a_section_is_refused() -> None:
    with pytest.raises(msgspec.ValidationError):
        Config.read({"session": {"secret": "s"}, "shop": {"curency": "PEN"}}, [ShopConfig])


def test_the_session_secret_is_required() -> None:
    with pytest.raises(msgspec.ValidationError):
        Config.read({"server": {"port": 80}}, [])


def test_put_replaces_a_section() -> None:
    config = Config(session=Config.read({"session": {"secret": "s"}}, []).session)
    config.put(ShopConfig(currency="EUR"))

    assert config.section(ShopConfig).currency == "EUR"
