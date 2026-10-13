# dooservice-kernel

A kernel for modular FastAPI services, extracted from the dooservice orchestrator so that
other services can start from the same base. It knows nothing about any feature: every
feature is a **module** that declares what it contributes, and the application that puts
modules together describes itself in a **profile**.

## What it gives an application

| Piece | What it does |
|---|---|
| `registry.Module` | The contract of a module: routers, Tortoise models, configuration sections, background listeners, startup hook and event subscriptions |
| `config.Config` | The TOML file: the kernel's `[server]`, `[database]`, `[session]` and `[cors]`, plus each module's own section, read into the struct the module declares. A section no module declares is refused |
| `events.Events` | What one module announces and others act on, without it knowing who listens |
| `application.ApplicationBuilder` | Builds the FastAPI app and runs its lifespan: logging, boundaries, database and migrations, module startup, listeners |
| `health` | `/health` and `/health/ready`, which asks the database and every boundary |
| `db`, `migrations`, `uow` | Tortoise on SQLite, native migrations with an optional baseline, transactions |
| `errors`, `problems`, `http` | Domain errors that carry their HTTP status, rendered as RFC 9457 problem documents, with a request id |
| `security`, `throttle`, `validated`, `field_rules` | Password hashing, signed cookies, a sealing cipher, rate limits and request field types |

## A module

```python
from typing import ClassVar

import msgspec
from fastapi import APIRouter

from dooservice_kernel.registry import Module


class ShopConfig(msgspec.Struct, forbid_unknown_fields=True):
    section: ClassVar[str] = "shop"      # its table in the config file

    currency: str = "USD"


class ShopModule(Module):
    name = "shop"
    config_sections = (ShopConfig,)
    orm_model_modules = ("shop.models",)

    def __init__(self) -> None:
        router = APIRouter(prefix="/orders")
        self.routers = (router,)
```

A module reads its section with `config.section(ShopConfig)`.

## An application

```python
from dooservice_kernel.application import ApplicationBuilder
from dooservice_kernel.config import Config
from dooservice_kernel.profile import Profile

config = Config.load([ShopConfig], env_var="SHOP_CONFIG")
builder = ApplicationBuilder(
    config,
    [ShopModule()],
    profile=Profile(title="shop", api_prefix="/api/v1", migrations="shop.migrations"),
    boundaries=[queue],                 # connect(), close(), ready(), unavailable()
    state={"queue": queue},             # what modules find on app.state
)
app = builder.build()
```

## Development

```sh
make install
make check          # ruff, basedpyright, pytest
make bump VERSION=0.2.0
```

Applications depend on it by tag:

```toml
[tool.uv.sources]
dooservice-kernel = { git = "https://github.com/dooservice/kernel", tag = "0.1.0" }
```
