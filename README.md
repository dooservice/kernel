# dooservice-kernel

An async kernel for modular FastAPI services, extracted from the
[dooservice](https://dooservice.sh) orchestrator so that other services can start from the
same base. It knows nothing about any feature: every feature is a **module** that declares
what it contributes, and the application that puts modules together describes itself in a
**profile**.

What sets it apart from a FastAPI template:

- **Each module brings its own configuration section.** The kernel reads its four; every
  other table in the TOML file is read into the struct the module that owns it declares,
  and a table nobody declares stops the service instead of being ignored.
- **Modules talk through events.** One announces, any other subscribes, and a handler
  that fails is logged without stopping the rest.
- **Boundaries.** What the service cannot work without (a message bus, a queue) is opened
  before the database, closed after it, and asked by `/health/ready` whether it is there.
- **A profile per application.** Its title, API prefix, migrations and the database it may
  have started from: nothing of one application is written into the kernel.

Everything is async: FastAPI, Tortoise ORM, the lifespan, the listeners and the events.

## What it gives an application

| Piece | What it does |
|---|---|
| `registry.Module` | The contract of a module: routers, Tortoise models, configuration sections, background listeners, startup hook and event subscriptions |
| `config.Config` | The TOML file: the kernel's `[server]`, `[database]`, `[session]` and `[cors]`, plus each module's own section, read into the struct the module declares. A section no module declares is refused |
| `events.Events` | What one module announces and others act on, without it knowing who listens |
| `application.ApplicationBuilder` | Builds the FastAPI app and runs its lifespan: logging, boundaries, database and migrations, module startup, listeners |
| `health` | `/health` and `/health/ready`, which asks the database and every boundary |
| `db`, `migrations`, `uow` | Tortoise ORM, native migrations with an optional baseline, transactions. SQLite only for now: the baseline check reads `sqlite_master` |
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

Applications depend on it by tag, as the dooservice orchestrator does:

```toml
[tool.uv.sources]
dooservice-kernel = { git = "https://github.com/dooservice/kernel", tag = "0.1.0" }
```

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, do not open an issue:
follow [SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE).
