# dooservice-kernel

An async kernel for modular FastAPI services. It was the core of the
[dooservice](https://dooservice.sh) orchestrator, where it runs some twenty modules in
production, and it is now a package of its own so that other services start from the same
base.

The kernel knows nothing about any feature. Every feature is a **module** that declares
what it contributes; the application that puts modules together describes itself in a
**profile**; and what the application cannot work without, a message bus or a queue, is a
**boundary** the kernel opens, closes and watches.

```
┌───────────────────────────── your application ─────────────────────────────┐
│   Profile: title, /api prefix, migrations      boundaries      app.state     │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                                 │
│   │  module  │   │  module  │   │  module  │   routers · models · config     │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘   listeners · events            │
└────────┼──────────────┼──────────────┼───────────────────────────────────────┘
         ▼              ▼              ▼
┌───────────────────────────── dooservice-kernel ────────────────────────────┐
│  config · registry · events · lifespan · health · database · migrations     │
│  errors as RFC 9457 · request id · security · throttle · field validation   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## What it brings

### Async from end to end

FastAPI for HTTP, Tortoise ORM for the database, an async lifespan, async listeners and
async event handlers. Nothing in the kernel blocks a worker, and nothing asks you to mix a
sync ORM into an async app.

### Modules with a contract

A module is a class. It declares what it adds and the kernel collects it at boot: the
kernel never imports a module, and a module never wires itself in.

```python
class Module:
    name: str
    routers: Sequence[APIRouter]            # mounted under the profile's prefix
    root_routers: Sequence[APIRouter]       # mounted at the root: webhooks
    orm_model_modules: Sequence[str]        # the Tortoise models it owns
    config_sections: Sequence[type]         # the configuration it reads

    provides: Sequence[type]                # the ports it offers others
    requires: Sequence[type]                # the ports it needs

    def listeners(self, app) -> Sequence[Listener]: ...      # background work: start() / stop()
    async def on_startup(self, app) -> None: ...             # register the ports it provides
    def subscriptions(self) -> Mapping[type, Handler]: ...   # the events it acts on
    def health_checks(self) -> Mapping[str, Check]: ...      # what /health/ready asks of it
    def commands(self) -> Sequence[Callable]: ...            # its commands on the command line
```

Two applications built from the same modules never share a router.

### Ports with a type, and the boot order worked out

A module says which ports it `provides` and which it `requires`, and asks for them by
type instead of by a name on `app.state`:

```python
class PlanLimits(Protocol):
    def projects(self) -> int: ...


class BillingModule(Module):
    name = "billing"
    provides = (PlanLimits,)

    async def on_startup(self, app) -> None:
        app.state.ports.provide(PlanLimits, StripeLimits())


class ProjectsModule(Module):
    name = "projects"
    requires = (PlanLimits,)
    # later: app.state.ports.get(PlanLimits).projects()
```

The kernel boots a module after every module that provides what it requires, whatever
order the application lists them in. **A requirement nobody provides, two modules that
require each other, or a provider that forgot to register its port all stop the boot**
with the names involved. A `default=True` implementation gives way to the real one a
later module provides.

### Modules as plugins

A package offers its modules under an entry point, and the application loads every
installed one:

```toml
[project.entry-points."dooservice_kernel.modules"]
shop = "shop.module:ShopModule"
```

```python
modules = ModuleDiscovery().installed()
```

`[modules]` in the configuration picks which run, by name, without touching code:
`enabled = ["shop", "ledger"]` keeps only those, `disabled = ["ledger"]` takes one out,
and a name that matches no module is refused.

### Each module brings its own configuration

The configuration is one TOML file. The kernel reads its four sections, `[server]`,
`[database]`, `[session]` and `[cors]`; every other table belongs to the module that
declares it:

```python
class ShopConfig(msgspec.Struct, forbid_unknown_fields=True):
    section: ClassVar[str] = "shop"      # its table in the file

    currency: str = "USD"
    tax_rate: float = 0.18


class ShopModule(Module):
    name = "shop"
    config_sections = (ShopConfig,)
```

```toml
[session]
secret = "…"

[shop]
currency = "PEN"
```

The module reads it with `config.section(ShopConfig)`, and a table missing from the file
comes with its defaults.

**The environment overrides any value and secrets come from files**, so one file serves
every deployment and no secret lives in it. With `Config.load(kinds, env_prefix="SHOP")`:

```sh
SHOP__SHOP__CURRENCY=PEN                       # [shop] currency = "PEN"
SHOP__SERVER__PORT=8080                        # read as TOML: a number
SHOP__SESSION__SECRET__FILE=/run/secrets/key   # [session] secret = the file's contents
``` Adding a module never means touching the kernel's configuration.
The file is checked strictly: **a table no module declares, or an unknown key inside one,
stops the service at boot** instead of being ignored. A misspelt section is found the
moment you deploy, not the day its value matters.

### Events between modules

One module announces something and any other acts on it; the one that announces never
knows who listens:

```python
class OrderPlaced(msgspec.Struct, frozen=True):
    order_id: uuid.UUID


class LedgerModule(Module):
    name = "ledger"

    def subscriptions(self) -> Mapping[type, Handler]:
        return {OrderPlaced: self.record}

    async def record(self, event: OrderPlaced) -> None: ...


await app.state.events.publish(OrderPlaced(order.id))
```

Handlers run in boot order and the publisher waits for all of them. **A handler that fails
is logged and the others still run**: one module leaving its part undone is no reason for
the rest to skip theirs. In the dooservice orchestrator this is how a deleted project is
cleaned from every module's tables, and how a daily reconcile clears whatever a deletion
missed.

**Events that must not be lost go through the outbox.** `Outbox.add(event)` writes the
event in the same transaction as the change it announces, and the outbox module's relay
publishes it afterwards: either both happen or neither does, and a process that stops
in between delivers it when it comes back. Include `OutboxModule()` among the modules and
`OutboxModule.table()` in one of your migrations.

**Events reach every process** with an event bridge. `RedisEventBridge` (the `redis`
extra) is a boundary and a bridge at once: an event published in one process reaches the
handlers of all of them, and never the same process twice.

```python
bridge = RedisEventBridge("redis://cache:6379/0")
ApplicationBuilder(config, modules, boundaries=[bridge], bridge=bridge)
```

### Boundaries

A boundary is what the service cannot work without: a message bus, a queue, a cache. It is
anything with four methods:

```python
class Boundary(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    def ready(self) -> bool: ...
    def unavailable(self) -> DomainError: ...   # what /health/ready answers while it is down
```

The kernel opens every boundary before the database and closes it after, and
`/health/ready` asks each one whether it is still there. A service that answers HTTP while
its bus is gone looks healthy and does nothing; with boundaries a monitor sees it, with the
error code the boundary chose.

### Health that says what fails

`/health/ready` answers the state of each check by name, the database, every boundary
and every check a module declares, so a monitor sees which one fails and not only that
one does:

```json
{"status": "ready", "checks": {"database": "ok", "redis events": "ok", "ledger.balance": "ok"}}
```

While a boundary is down it answers with that boundary's own error; while only a
module's check fails, `503` with `not_ready` and the checks that fail.

### Work on a timer

`Periodic` is the listener for a sweep, a reconcile, a relay: it waits `first_after`
before the first run, runs every `every` seconds with a little jitter so processes do
not run in step, logs a run that fails and keeps going.

```python
def listeners(self, app):
    return (Periodic("reconcile", self.reconcile, every=86400, first_after=600),)
```

### A command line with each module's commands

```python
command_line = CommandLine("shop", modules, load_config)
command_line()            # shop check-config · shop ledger rebuild --since 2026-01-01
```

Each module's `commands()` go under its name, and `check-config` reads the configuration
the way the service would, every module's section included, and stops.

### A profile per application

Nothing of one application is written into the kernel: its name in the API docs, the prefix
its modules are mounted under, the cookie that carries the OAuth state, the package of its
migrations, and the database it may have started from before it had migrations.

```python
Profile(
    title="shop",
    api_prefix="/api/v1",
    state_cookie="shop_oauth_state",
    migrations="shop.migrations",
    baseline=Baseline(migration="0001_initial", sentinel_table="users"),
)
```

### A lifespan in a fixed order

Boot: logging, boundaries, database and migrations, each module's `on_startup`, listeners.
Shutdown runs it backwards: listeners, database, boundaries. One place knows the order, so
no module has to.

### Database and migrations

Tortoise ORM with its native migrations, run at startup, on **SQLite or PostgreSQL** (the
`postgres` extra); the tests run against both. A **baseline** lets a database
that predates migrations adopt them: when its sentinel table is there and the migrations
table is not, the first migration is stamped as applied without running any SQL, so
existing data is never touched. Tests can skip migrations and generate the schema
(`use_generated_schemas=True`). `UnitOfWork.atomic()` wraps writes that span tables.

### Errors that know their HTTP answer

A domain error carries its status, code and title:

```python
class OrderNotFoundError(NotFoundError):
    code = "order_not_found"
    title = "Order Not Found"
```

Raised anywhere, it is answered as an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)
problem document with that code and the request id. A request that fails validation is
answered 422 with **each field and its own code** (`invalid_email`, `invalid_domain`…), so
a client can say exactly what is wrong. An unexpected exception is logged and answered as a
500 that gives nothing away. Errors never register their own handlers.

Categories ready to subclass: `BadRequestError` 400, `UnauthorizedError` 401,
`ForbiddenError` 403, `NotFoundError` 404, `ConflictError` 409, `LockedError` 423,
`RateLimitedError` 429, `UpstreamError` 502, `UnavailableError` 503.

### Request id in every answer and every log line

Every request gets an id, returned as `X-Request-Id`, written in every log line it causes
and in every problem document, so a user's screenshot of an error leads straight to the
logs. Background work can carry a job id the same way. With `[server] log_format = "json"`
each line is one JSON object, for whatever collects the logs.

### Metrics and traces

Extensions the application passes to the builder, each with its extra:

```python
ApplicationBuilder(config, modules, extensions=[Metrics(), Tracing()])
```

- `Metrics` (the `metrics` extra) serves `/metrics` for Prometheus: requests by method,
  route template and status, their duration, and whether each boundary is ready. A route
  is counted by its template, so ids do not make one series each.
- `Tracing` (the `tracing` extra) makes every request an OpenTelemetry span; where spans
  go is OpenTelemetry's own configuration.

### Security primitives

- `PasswordHasher`: bcrypt.
- `CookieSigner`: signed, time-limited values for cookies.
- `SecretCipher`: seals values at rest with a key derived from a secret and a purpose, so
  two ciphers of one secret cannot read each other. Values sealed before the cipher existed
  are recognised and passed through, so a column can be encrypted gradually.
- `OtpGenerator` and `TokenGenerator`: one-time codes and URL-safe tokens.
- `Throttle`: how many attempts per key in a window, for passwords and codes, kept in
  memory; `RedisThrottle` (the `redis` extra) shares the counts between processes.

### Request field types

Annotated types that check a value before any function sees it, each refusing with its own
code: `EmailAddress` (trimmed, lowered, checked), `DnsLabel`, `CustomDomain`,
`TimeZoneName`, `Password`, `DisplayName`, `OtpCode`, `LanguageCode`, `StorageEndpoint`
(https only) and more. Plain string rules, no regular expressions.

### Testing a module in a few lines

`KernelHarness` (the `testing` extra) builds the app with your modules, an in-memory
database with the schema generated and the lifespan running, and gives you a client.
Its pytest plugin hands it over as the `kernel_harness` fixture:

```python
async def test_orders(kernel_harness) -> None:
    bus = FakeBoundary("bus")
    async with kernel_harness([ShopModule()], sections=[ShopConfig(currency="PEN")], boundaries=[bus]) as shop:
        assert (await shop.client.get("/api/orders")).status_code == 200
        bus.up = False
        assert (await shop.client.get("/health/ready")).status_code == 503
```

### It stays generic

A test fails if the kernel imports anything but the standard library and its own
dependencies. Whatever is built on it plugs into it, never the other way round.

## An application

```python
from dooservice_kernel.application import ApplicationBuilder
from dooservice_kernel.config import Config
from dooservice_kernel.profile import Profile

config = Config.load([ShopConfig], env_var="SHOP_CONFIG")
builder = ApplicationBuilder(
    config,
    [ShopModule(), LedgerModule()],
    profile=Profile(title="shop", api_prefix="/api/v1", migrations="shop.migrations"),
    boundaries=[queue],
    state={"queue": queue},          # what modules find on app.state
)
app = builder.build()                # serve it with uvicorn
```

`app.state` also carries `config`, `registry`, `events`, `cookie_signer` and
`password_hasher`.

## Extras

| Extra | Brings |
|---|---|
| `postgres` | PostgreSQL through asyncpg |
| `redis` | `RedisEventBridge` and `RedisThrottle` |
| `metrics` | `Metrics` for Prometheus |
| `tracing` | `Tracing` with OpenTelemetry |
| `testing` | `KernelHarness`, `FakeBoundary` and the pytest plugin |

## Limits

- **SQLite and PostgreSQL.** MySQL is answered by the table check but not tested.
- **Delivery between processes is at most once** over the Redis bridge; what must not be
  lost goes through the outbox, which is at least once, so its handlers must not mind
  seeing an event twice.
- **Young.** It is 0.x: the module contract and the profile may still change between minor
  versions, and the changelog says how.

## Development

```sh
make install
make check          # ruff, basedpyright, pytest
make bump VERSION=0.2.0
```

Applications depend on it by tag, as the dooservice orchestrator does:

```toml
[tool.uv.sources]
dooservice-kernel = { git = "https://github.com/dooservice/kernel", tag = "0.2.0" }
```

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, do not open an issue:
follow [SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE).
