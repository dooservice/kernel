from __future__ import annotations

from pathlib import Path

from dooservice_kernel.overrides import EnvironmentOverrides


def test_the_environment_overrides_values_and_reads_them_as_toml() -> None:
    environ = {"SHOP__SERVER__PORT": "8080", "SHOP__SHOP__CURRENCY": "PEN", "SHOP__CORS__ORIGINS": '["https://a.b"]'}

    data = EnvironmentOverrides("SHOP", environ).apply({"server": {"host": "0.0.0.0"}})

    assert data == {
        "server": {"host": "0.0.0.0", "port": 8080},
        "shop": {"currency": "PEN"},
        "cors": {"origins": ["https://a.b"]},
    }


def test_a_secret_is_read_from_a_file(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("s3cret\n")

    data = EnvironmentOverrides("SHOP", {"SHOP__SESSION__SECRET__FILE": str(secret)}).apply({})

    assert data == {"session": {"secret": "s3cret"}}


def test_without_a_prefix_nothing_is_read_from_the_environment() -> None:
    assert EnvironmentOverrides("", {"X__SERVER__PORT": "1"}).apply({"a": {}}) == {"a": {}}
