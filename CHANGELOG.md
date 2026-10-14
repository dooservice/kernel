# Changelog

All notable changes to `dooservice-kernel` are documented here.

## [0.4.0] — 2026-10-15

### Changed
- Every constant of the kernel lives in `dooservice_kernel.constants`, instead of at the top
  of the module that used it: `DEFAULT_CONFIG_PATH`, `CONFIG_ENV_VAR`, `MIGRATIONS_TABLE`,
  `PROBLEM_CONTENT_TYPE` and the rest are imported from there now.

## [0.3.1] — 2026-10-14

### Changed
- No module-level functions left but the `kernel_harness` fixture, which pytest only finds
  as one: `KernelDependencies.provide_config` (and its siblings) and
  `ClientAddress.client_address`. The `Annotated` aliases (`AppConfig`, …) are unchanged.

## [0.3.0] — 2026-10-14

### Added
- `Ports.of(app)`: the ports of an application with their type, from the app or from a
  request's `app`, so `ports.get(PlanLimits)` is a `PlanLimits` and not whatever
  `app.state` holds.
- `Ports.replace(kind, implementation)`: how a test stands a fake in for what the
  application provided. Only a port that was provided can be replaced.
- More kinds of value in `validated`, each a rule written once: `Label`, `Description`,
  `TextLine`, `Identifier` and `OptionalIdentifier` (a UUID, kept in one spelling),
  `Secret`, `Opaque`, `ProviderCode` (a provider's region or size), `LanguageTag`,
  `CountryCode`, `Sha256`, `ByteCount` and `OptionalEmailAddress`. They refuse with
  `invalid_identifier`, `invalid_option`, `invalid_language`, `invalid_country` and
  `invalid_digest`. Plain string methods, no patterns.

### Fixed
- A module that fails to start no longer leaves the process waiting: the listeners that
  started, the database and the boundaries are closed in reverse order and the error
  reaches whoever started the application. Before, the database's thread kept the
  process alive with nothing on screen.

## [0.2.1] — 2026-10-14

### Changed
- `[session] cookie_samesite` is `lax`, `strict` or `none`, and `[server] log_format` is
  `text` or `json`, checked when the configuration is read: an application passes them on
  with their type instead of a string anything could be.
- `make check` runs lint, formatting, types and tests over `src` and `tests`, and CI runs
  exactly that.

### Fixed
- The outbox model's `Meta` extends `Model.Meta` instead of silencing the type checker.

## [0.2.0] — 2026-10-13

### Added
- **PostgreSQL** (the `postgres` extra): migrations and the baseline check work on SQLite
  and PostgreSQL, and the tests run against both.
- **Ports with a type and the boot order worked out**: `Module.provides` and `requires`,
  `app.state.ports.provide()` and `get()`. A requirement nobody provides, a cycle, or a
  provider that did not register its port stops the boot.
- **Modules as plugins**: `ModuleDiscovery` loads those offered under the
  `dooservice_kernel.modules` entry points, and `[modules] enabled` / `disabled` picks
  which run.
- **A command line**: `CommandLine` puts each module's `commands()` under its name and
  adds `check-config`.
- **Configuration from the environment**: `PREFIX__SECTION__KEY` overrides a value, read as
  TOML, and `PREFIX__SECTION__KEY__FILE` reads a secret from a file.
- **Observability**: `[server] log_format = "json"`; `Metrics` (Prometheus, the `metrics`
  extra) and `Tracing` (OpenTelemetry, the `tracing` extra) as extensions passed to the
  builder.
- **Reliable events**: the outbox (`OutboxModule`, `Outbox.add`) delivers at least once
  what was written with the change it announces; `RedisEventBridge` carries events
  between processes; `RedisThrottle` shares attempt counts.
- **Health that says what fails**: `/health/ready` lists every check by name, and modules
  add their own with `health_checks()`.
- **Work on a timer**: `Periodic`.
- **Testing**: `KernelHarness`, `FakeBoundary` and the `kernel_harness` pytest fixture (the
  `testing` extra).

### Changed
- The kernel's own sections live in `sections.py`; `config` still exports them.
- `ApplicationBuilder` takes `extensions` and `bridge`.

## [0.1.1] — 2026-10-13

### Changed
- **Open source, under the Apache License 2.0**, with a security policy, contribution
  guide, code of conduct and issue templates. The README says what sets the kernel apart
  and that the database is SQLite for now.

## [0.1.0] — 2026-10-13

### Added
- **The kernel of the dooservice orchestrator, on its own.** Modules declare their
  routers, models, configuration sections, listeners and event subscriptions; the
  kernel reads the configuration file, opens the database and runs its migrations,
  opens the application's boundaries, mounts the modules under the profile's prefix and
  answers `/health` and `/health/ready`. It names no product: the application describes
  itself in a `Profile`.
