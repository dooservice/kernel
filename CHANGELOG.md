# Changelog

All notable changes to `dooservice-kernel` are documented here.

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
