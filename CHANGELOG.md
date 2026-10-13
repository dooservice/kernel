# Changelog

All notable changes to `dooservice-kernel` are documented here.

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
