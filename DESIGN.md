# tunning Design

`tunning` is a small Python logging helper for CLI applications. It wraps
stdlib `logging` and `rich` so an app can emit readable terminal logs and
detailed rotating file logs from one YAML-driven configuration.

The current runtime API is `TunnedLogger.from_yaml(...)`.

## Problem

CLI projects often need the same logging setup repeatedly:
- readable terminal output
- consistent colors, symbols, and icons
- optional custom log levels
- file logging with rotation
- a simple way to configure all of this per project

The goal is to avoid rewriting custom logger setup in every CLI app while still
remaining compatible with stdlib `logging`.

## Current Status

This project is an early package prototype. The core flow is implemented and the
package identity is now `tunning`.

Implemented:
- `TunnedLogger.from_yaml(...)` as the main runtime entrypoint
- package import through `tunning`
- package metadata in `pyproject.toml`
- MIT license metadata
- packaged default config in `tunning/conf.yml`
- YAML default loading and deep-merge override loading
- named logger configuration without configuring the process root logger
- `TunnedHandler` for console output prefixes
- rotating file handler support through stdlib `logging.handlers`
- custom level metadata through top-level `levels:`
- dynamic custom level methods such as `trace()` and `success()`
- top-level `prompt:` styling through `logger.prompt(...)`
- validation for built-in level codes
- rejection of `WARN`/`FATAL` aliases in `levels:`
- rejection of `levels.INPUT` in favor of top-level `prompt:`
- human-readable `maxBytes` normalization
- automatic parent directory creation for file handlers
- pytest coverage in `tests/test_tunned_logger.py`
- example script under `examples/`
- user-facing config reference in `README.md`

Not implemented yet:
- CLI entrypoint
- CI, linting, type checking, or pre-commit configuration
- box/panel rendering mode
- message body color customization

## Architecture

Implementation lives in `tunning/logger.py`.

Public classes:
- `TunnedLogger`: a `logging.Logger` subclass with `from_yaml(...)` and
  `prompt(...)`
- `TunnedHandler`: a `rich.logging.RichHandler` subclass that renders level
  prefixes from configured symbols or icons

Package files:
- `tunning/__init__.py`: public exports
- `tunning/logger.py`: implementation
- `tunning/conf.yml`: packaged default config

Examples:
- `examples/basic_usage.py`: prototype usage example
- `examples/conf.yml`: full config example
- `examples/custom_logger.yml`: sample partial override

Test file:
- `tests/test_tunned_logger.py`

## Configuration Model

`TunnedLogger.from_yaml(config_path, name=..., force=...)` loads packaged
defaults first, then deep-merges the provided YAML override on top.

Top-level `levels:` defines log level metadata:
- `code`: numeric logging level
- `symbol`: terminal prefix when icons are disabled
- `icon`: terminal prefix when icons are enabled
- `style`: Rich style for the prefix

Top-level `prompt:` defines prompt styling separately from log levels:
- `symbol`: prompt prefix when icons are disabled
- `icon`: prompt prefix when icons are enabled
- `style`: Rich style for the prompt prefix

Logging config uses stdlib `logging.config.dictConfig` shape after normalization.
Only the requested named logger is configured. If a config only defines `root:`,
that section is used as the template for the requested named logger. It does not
configure the actual process root logger.

## Logging Rules

Built-in levels must keep stdlib level codes:
- `DEBUG=10`
- `INFO=20`
- `WARNING=30`
- `ERROR=40`
- `CRITICAL=50`

Use `WARNING`, not `WARN`. Use `CRITICAL`, not `FATAL`.

Custom levels are process-global because stdlib logging level registration is
process-global. Reconfiguring handlers with `force=True` is allowed for the same
named logger, but conflicting custom level redefinitions are rejected.

## Roadmap

### 1. Stabilize Existing Behavior

Status: complete for the first stabilization pass.

The current priority remains preserving the API and adding tests before adding
new features.

The first stabilization pass added tests for:
- default and override deep-merge behavior
- custom level conflict detection
- `WARN` and `FATAL` alias rejection
- `levels.INPUT` rejection
- invalid `show_icon` usage on non-rich handlers
- invalid human-readable `maxBytes` values
- explicit `loggers:` configuration for the requested logger
- fallback prompt behavior when no `TunnedHandler` exists
- dynamic method name conversion, for example `MY-CUSTOM-LEVEL` to
  `my_custom_level()`

### 2. Clean Development Surface

Status: complete for the initial cleanup.

The previous `src/helper.py` scratch script has been moved to
`examples/basic_usage.py`.

The old `src/` implementation layout has been replaced by the root package
directory `tunning/`.

### 3. Improve Documentation

Status: started.

Keep `README.md` focused on user-facing usage.

Keep this file focused on architecture, design constraints, and roadmap.

The README now includes a config reference covering:
- `levels:`
- `prompt:`
- handler options
- symbols vs icons
- file rotation
- reconfiguration rules

### 4. Package The Library

Status: started.

Current packaging work:
- distribution name is `tunning`
- import package is `tunning`
- public logger class is `TunnedLogger`
- public handler class is `TunnedHandler`
- base runtime dependencies are limited to logging/config support
- optional extras provide `cli` (`typer`) and `tui` (`textual`) dependencies
- `requirements.txt` is the full developer dependency set
- release metadata includes MIT license, author, repository URL, and issue tracker URL
- build tooling is included in the `dev` extra
- editable install behavior has been verified with all extras

Remaining packaging work:
- decide whether to add documentation URLs once docs are ready

### 5. Optional Future Features

Future features should wait until the existing behavior is well covered.

Potential features:
- `message_color`: optionally color the whole message instead of only the level
  prefix
- `boxes`: render each log event in a Rich panel/box using the level style
- richer example configs
- optional CLI/demo command

## Non-Goals For Now

- Do not wrap `Typer`; this library should stay focused on logging.
- Do not implement a TUI abstraction; use `Textual` directly for that.
- Do not add compatibility shims for old config shapes unless there is a clear
  external user or persisted config need.
