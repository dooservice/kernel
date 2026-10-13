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

    def listeners(self, app) -> Sequence[Listener]: ...      # background work: start() / stop()
    async def on_startup(self, app) -> None: ...             # publish ports on app.state
    def subscriptions(self) -> Mapping[type, Handler]: ...   # the events it acts on
```

Modules boot in the order the application lists them, so a lower module can publish a
port on `app.state` that a higher one reads. Two applications built from the same modules
never share a router.

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
comes with its defaults. Adding a module never means touching the kernel's configuration.
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

Tortoise ORM with its native migrations, run at startup. A **baseline** lets a database
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
logs. Background work can carry a job id the same way.

### Security primitives

- `PasswordHasher`: bcrypt.
- `CookieSigner`: signed, time-limited values for cookies.
- `SecretCipher`: seals values at rest with a key derived from a secret and a purpose, so
  two ciphers of one secret cannot read each other. Values sealed before the cipher existed
  are recognised and passed through, so a column can be encrypted gradually.
- `OtpGenerator` and `TokenGenerator`: one-time codes and URL-safe tokens.
- `Throttle`: how many attempts per key in a window, for passwords and codes.

### Request field types

Annotated types that check a value before any function sees it, each refusing with its own
code: `EmailAddress` (trimmed, lowered, checked), `DnsLabel`, `CustomDomain`,
`TimeZoneName`, `Password`, `DisplayName`, `OtpCode`, `LanguageCode`, `StorageEndpoint`
(https only) and more. Plain string rules, no regular expressions.

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

## Limits

- **SQLite only, for now**: the baseline check reads `sqlite_master`. The other databases
  Tortoise supports need that check made portable.
- **One process.** `Throttle` keeps its counts in memory and events are delivered in
  process; several workers would each have their own.
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
dooservice-kernel = { git = "https://github.com/dooservice/kernel", tag = "0.1.1" }
```

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, do not open an issue:
follow [SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE).
