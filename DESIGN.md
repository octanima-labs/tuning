# tuning Design

`tuning` is a small Python logging helper for CLI applications. It wraps
stdlib `logging` and `rich` so an app can emit readable terminal logs and
detailed rotating file logs from programmatic or YAML-driven configuration.

The preferred runtime APIs are `tuning.getLogger(...)`,
`tuning.basicConfig(...)`, and `tuning.basicConfigFromYaml(...)`.
`TunedLogger.from_yaml(...)` remains available for configuring one named logger
directly.

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
package identity is now `tuning`.

Implemented:
- `tuning.getLogger(...)` for creating named `TunedLogger` instances
- `tuning.basicConfig(...)` for stdlib-like root logger configuration
- `tuning.basicConfigFromYaml(...)` for root logger configuration from YAML
- lazy console-only zero configuration when loggers are used before explicit configuration
- `TunedLogger.from_yaml(...)` for named logger configuration
- package import through `tuning`
- package metadata in `pyproject.toml`
- MIT license metadata
- packaged default config in `tuning/conf.yml`
- YAML default loading and deep-merge override loading
- `tuning.export(...)` for writing a full starter YAML config
- root logger configuration with stdlib-like inheritance for child loggers
- named logger configuration without configuring the process root logger
- `TunedHandler` for console output prefixes
- rotating file handler support through stdlib `logging.handlers`
- custom level metadata through top-level `levels:`
- dynamic custom level methods such as `trace()` and `success()`
- top-level `prompt:` styling through `logger.prompt(...)`
- full console message styling using each level's `style`
- optional per-record Rich panel rendering with `boxes`
- validation for built-in level codes
- rejection of `WARN`/`FATAL` aliases in `levels:`
- rejection of `levels.INPUT` in favor of top-level `prompt:`
- human-readable `maxBytes` normalization
- automatic parent directory creation for file handlers
- pytest coverage in `tests/test_tuned_logger.py`
- Ruff linting and formatting configuration
- mypy type checking configuration
- pre-commit hook configuration
- GitHub Actions CI across Python 3.11 through 3.14
- Sphinx documentation generated from public API docstrings
- example script under `examples/`
- user-facing config reference in `README.md`

There is no package CLI entrypoint by design. The example script has its own
demo parser, but `tuning` remains a logging library. Message body styling is
implemented as current behavior: each level's `style` always applies to the full
console message text.

## Architecture

Logging implementation lives in `tuning/logger.py`. Banner rendering lives in
`tuning/_banners.py`.

Public classes:
- `TunedLogger`: a `logging.Logger` subclass with `from_yaml(...)` and
  `prompt(...)`
- `TunedHandler`: a `rich.logging.RichHandler` subclass that renders level
  prefixes from configured symbols or icons

Public functions:
- `getLogger(...)`: create or return a named `TunedLogger`
- `basicConfig(...)`: configure the real process root logger programmatically
- `basicConfigFromYaml(...)`: configure the real process root logger from YAML
- `banner(...)`: print a styled app banner from a project `banners.txt` file
- `export(...)`: write the packaged default YAML config to a project file

Package files:
- `tuning/__init__.py`: public exports
- `tuning/logger.py`: implementation
- `tuning/_banners.py`: banner file discovery, parsing, selection, and rendering
- `tuning/conf.yml`: packaged default config
- `docs/`: generated API reference and guide pages
- `docs/conf.py`: documentation site configuration

Examples:
- `examples/usage.py`: prototype usage example with selectable config modes
- `examples/banners.txt`: sample app banner file for the usage example
- `examples/conf.yml`: full config example
- `examples/custom_logger.yml`: sample partial override

Test files:
- `tests/test_banners.py`
- `tests/test_tuned_logger.py`

## Configuration Model

`basicConfigFromYaml(config_path, force=...)` and
`TunedLogger.from_yaml(config_path, name=..., force=...)` load packaged defaults
first, then deep-merge the provided YAML override on top.

Top-level `levels:` defines log level metadata:
- `code`: numeric logging level
- `symbol`: terminal prefix when icons are disabled
- `icon`: terminal prefix when icons are enabled
- `style`: Rich style for the console prefix and full message text

Top-level `prompt:` defines prompt styling separately from log levels:
- `symbol`: prompt prefix when icons are disabled
- `icon`: prompt prefix when icons are enabled
- `style`: Rich style for the prompt prefix and prompt text

Level styles apply only to the console prefix, the separator before the message,
and the full message text. There is no `message_color` opt-out. Prompt styles
apply only to the rendered prompt prefix and question text, not the trailing
input spacer or the user's answer. Time/path columns and file handlers are not
styled by level metadata.
When `boxes` is enabled on `TunedHandler`, each console log record is rendered
in its own Rich panel. The panel border, title, padding, and fill use the level
style. Time and path columns stay outside the panel and remain structural.
Tracebacks render inside the same panel as the message. Consecutive records are
not grouped.
The console level prefix column has a minimum width of 3 terminal cells; longer
fallback labels expand naturally.

Logging config uses stdlib `logging.config.dictConfig` shape after normalization.
`basicConfigFromYaml(...)` preserves `root:` as the actual process root logger.
When called without a path, it loads only the packaged `tuning/conf.yml`.
`export(...)` writes the packaged `tuning/conf.yml` text as a full standalone
YAML file. It intentionally does not reconstruct live runtime logger state,
because stdlib logging handlers are not reliably serializable back to config.
`TunedLogger.from_yaml(...)` configures only the requested named logger. In that
named mode, if a config only defines `root:`, that section is used as the
template for the requested named logger and does not configure the actual process
root logger.

`basicConfig(...)` follows stdlib behavior: it configures the root logger only if
the root has no handlers, unless `force=True` is passed. Its default level is
`WARNING`. Without `filename`, it installs a console `TunedHandler`; with
`filename`, it installs a detailed file handler only. Passing `console=True` with
`filename` installs both file and console handlers. Programmatic file rotation is
enabled by passing `max_bytes` or `backup_count`; if only one is provided, the
other uses `DEFAULT_MAX_BYTES` or `DEFAULT_BACKUP_COUNT` with a warning. Rotation
options are ignored when `filename` is omitted. Console-only options are
`show_icon`, `show_level`, `show_path`, `show_time`, `boxes`, `rich_tracebacks`,
and `markup`; they do not affect file handlers.

If a `TunedLogger` is used before explicit configuration, `tuning` lazily
installs packaged level metadata and a console-only root `TunedHandler` at INFO
level. It does not replace root handlers that already exist.

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
`addLevel(...)` registers runtime-only custom levels through the same global
registry and installs the matching dynamic `TunedLogger` method. It does not
mutate YAML files or exported configuration.

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
- fallback prompt behavior when no `TunedHandler` exists
- dynamic method name conversion, for example `MY-CUSTOM-LEVEL` to
  `my_custom_level()`

### 2. Clean Development Surface

Status: complete for the initial cleanup.

The previous `src/helper.py` scratch script has been consolidated into
`examples/usage.py`.

The old `src/` implementation layout has been replaced by the root package
directory `tuning/`.

### 3. Improve Documentation

Status: complete for the current prototype.

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

Status: complete for the current prototype.

Implemented packaging work:
- distribution name is `tuning`
- import package is `tuning`
- public logger class is `TunedLogger`
- public handler class is `TunedHandler`
- base runtime dependencies are limited to logging/config support
- optional extras provide `cli` (`typer`) and `tui` (`textual`) dependencies
- `requirements.txt` is the full developer dependency set
- release metadata includes MIT license, author, repository URL, and issue tracker URL
- build tooling is included in the `dev` extra
- editable install behavior has been verified with all extras

Packaging follow-up:
- decide whether to add documentation URLs once a docs site exists

### 5. Quality Gates

Status: complete for the initial setup.

Current quality tooling:
- pytest for behavioral tests
- Ruff for linting and formatting
- mypy for type checking
- pre-commit hooks for local validation
- GitHub Actions CI for Python 3.11, 3.12, 3.13, and 3.14

### 6. Optional Future Features

Future features should wait until the existing behavior stays well covered.

Potential features:
- [X] full message styling: level styles always color the whole console message
- [X] `boxes`: render each log event in a Rich panel/box using the level style
- [X] richer example configs
- [X] optional CLI/demo command

Grouped boxes remain a possible follow-up feature, not part of the current
stabilized runtime scope.

## Non-Goals For Now

- Do not wrap `Typer`; this library should stay focused on logging.
- Do not implement a TUI abstraction; use `Textual` directly for that.
- Do not add compatibility shims for old config shapes unless there is a clear
  external user or persisted config need.

## `Boxes` Feature


Implemented shape:

```
╭─ SYMBOL/ICON/LOG_LEVEL ───────────────────────────╮
│ Here goes the message.                            │
│ It may be multiline                               │
╰───────────────────────────────────────────────────╯
```
The `box` border, title, padding, and fill use the same styling as the message.

Rules:
- `show_time` renders outside the box in the existing time column.
- `show_path` renders outside the box in the existing path column.
- `show_level` controls the box title. If disabled, the box has no title.
- Tracebacks render inside the same box as the message.
- Each log record gets its own box. Grouping consecutive records can be added
  later if buffering and flush semantics are worth the complexity.

## TODOs

- [X] Console handler allows disabling symbol/icon/lvl_name completely with `basicConfig(show_level=False)`, matching YAML `show_level` behavior.
- [X] Add new API function to add your own levels during run-time: `tuning.addLevel()`
- [X] Review readme and related conf. Remove development and "internal" comments from there.
- [X] Design a banner/icon for the library.
  - [X] Basic banner in place
  - [X] Improve banner, make it more "tuned".
- [X] Improve docs
  - [X] Make the icon smaller in the docs and `README.md`
  - [X] Update favicon.
  - [X] Section navigation seems to be ~~broken~~ -> **unused**
- [X] Migrate documentation to Sphinx + MyST + PyData theme.
- [ ] When all the previous are done, upgrade version to 1.0 and publish
- Version 1.1:
  - [ ] Add pictures to the readme/conf
  - [ ] Add [`rich-gradient`](https://github.com/maxludden/rich-gradient) support. Maybe only as optional dependency, Im not sure if any wrapper is necessary.
  - [ ] In panel, allow to control:
    - [ ] Optional, not shown by default: show version in the banner (from toml)
    - [ ] Optional, not shown by default: show author in the banner (from toml)
    - [ ] Optional, not shown by default: show foot note in the banner (from toml, might require creating a custom key)
