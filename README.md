# tunning

`tunning` is a small but stylish Python logging helper for CLI apps.

It builds on stdlib `logging` and `rich` to give you:
- colored console output through `TunnedHandler`
- rotating file logs through normal `logging` handlers
- stdlib-like root logger configuration through `basicConfig()`
- YAML-driven configuration
- custom levels such as `TRACE` and `SUCCESS`
- a styled `prompt()` helper for interactive CLI input

> Optional extras are available for CLI and TUI integrations, but `tunning` does not wrap Typer or Textual.

## Install

```bash
pip install tunning
```

Optionally include extras for CLI or TUI integrations:

```bash
pip install "tunning[cli]"
pip install "tunning[tui]"
pip install "tunning[cli,tui]"
```

To install directly from the repository:

```bash
pip install "tunning[cli,tui] @ git+https://github.com/octanima-labs/tunning"
```

For development, clone the repo and install with the `dev` extra:

```bash
git clone https://github.com/octanima-labs/tunning
cd tunning
pip install -e ".[dev,cli,tui]"
```

Project metadata lives in `pyproject.toml`. Build tooling is included in the
`dev` extra and in `requirements.txt`.

## Quick start

```python
import tunning

logger = tunning.getLogger(__name__)

logger.info("application started")
logger.success("everything looks good")

name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

This zero-config path installs packaged console defaults lazily on first use.

Use a log file with the stdlib-style API:

```python
import tunning

logger = tunning.getLogger(__name__)

tunning.basicConfig(filename="myapp.log", level="INFO")
logger.info("application started")
```

Use a log file and console output together with `console=True`:

```python
tunning.basicConfig(
    filename="myapp.log",
    console=True,
    level="INFO",
    show_icon=True,
)
```

Call `basicConfig(...)` when you want to override the programmatic defaults:

```python
tunning.basicConfig(level="INFO")
```

Use YAML when you want the packaged `tunning/conf.yml` defaults, optionally plus an override:

```python
import tunning

logger = tunning.getLogger(__name__)

tunning.basicConfigFromYaml("examples/custom_logger.yml")
logger.success("everything looks good")
```

`tunning.basicConfigFromYaml()` with no path loads the packaged YAML defaults.

Export a full starter config into your project:

```python
import tunning

config_path = tunning.export()
```

With no path, `export()` writes `tunning.yml` next to the Python file that
called it. Pass a file path to choose the exact destination, or an existing
directory to write `<directory>/tunning.yml`. Existing files are not overwritten
unless you pass `force=True`.

## How configuration works
- `tunning.basicConfig()` configures the actual process root logger, like `logging.basicConfig()`.
- Calling logger methods before explicit configuration installs console-only zero-config defaults.
- `basicConfig(filename=...)` creates a file handler only.
- `basicConfig(filename=..., console=True)` creates both file and console handlers.
- Repeated `basicConfig()` calls do nothing unless `force=True`.
- `tunning.basicConfigFromYaml()` loads the packaged default config from `tunning/conf.yml` first.
- `basicConfigFromYaml()` with no path loads only the packaged default config.
- The YAML file you pass in is deep-merged on top of those defaults.
- `basicConfigFromYaml()` preserves `root:` as the real process root logger config.
- `examples/conf.yml` shows a full config with the same shape as the packaged defaults.
- `examples/custom_logger.yml` is intentionally a partial override, not a standalone full config.
- `tunning.export(...)` writes the packaged default config as a full standalone YAML file.
- If your YAML only defines `root:`, that section is used as the template for the named logger returned by `from_yaml(...)`.
- The actual process root logger is not configured by `from_yaml(...)`.

## Config features
- Top-level `levels:` defines custom level metadata.
- Top-level `prompt:` defines the style used by `logger.prompt(...)`.
- `show_icon: true` on `TunnedHandler` switches console prefixes from symbols to icons.
- Human-readable file sizes such as `"5 MB"` are accepted for `maxBytes`.
- Parent directories for file handlers are created automatically.

Built-in levels must keep stdlib codes:
- `DEBUG=10`
- `INFO=20`
- `WARNING=30`
- `ERROR=40`
- `CRITICAL=50`

Use `WARNING`, not `WARN`. Use `CRITICAL`, not `FATAL`.

Custom levels become methods on `TunnedLogger`. For example, a `TRACE` level creates `logger.trace(...)`.

## Example config
The default config in `tunning/conf.yml` defines:
- console logging through `TunnedHandler`
- rotating file logging to `.logs/app.log`
- custom levels like `TRACE`, `SUCCESS`, and `MY-CUSTOM-LEVEL`
- prompt styling through a top-level `prompt:` section

The sample override in `examples/custom_logger.yml` changes only a few console options and the logger level:

```yaml
handlers:
  console:
    level: DEBUG
    show_time: true
    show_path: true
    show_icon: true

root:
  level: DEBUG
```

## Config reference

### `basicConfig()`

`basicConfig()` configures the real process root logger programmatically:

```python
tunning.basicConfig(
    level="INFO",
    filename=None,
    max_bytes=None,
    backup_count=None,
    show_icon=False,
    show_path=False,
    show_time=False,
    datefmt=None,
    boxes=False,
    rich_tracebacks=True,
    markup=True,
)
```

Console options:
- `show_icon`: use configured level icons instead of symbols
- `show_path`: show source file path in console output
- `show_time`: show timestamps in console output
- `datefmt`: customize console timestamps when `show_time` is enabled
- `boxes`: render each console log record in a Rich box/panel
- `rich_tracebacks`: render Rich tracebacks in console output
- `markup`: allow Rich markup in console messages

Use `tunning.ISO_FORMAT` for ISO-style console timestamps:

```python
tunning.basicConfig(
    level="INFO",
    show_time=True,
    datefmt=tunning.ISO_FORMAT,
)
```

These options only apply to the generated console `TunnedHandler`.

File behavior:
- `filename="app.log"` creates a file handler only.
- `filename="app.log", console=True` creates both file and console handlers.
- File handlers use detailed text formatting and do not use icons.
- `max_bytes` enables rotating file logs and accepts bytes or size strings like `"10 MB"`.
- `backup_count` controls how many rotated log files are kept.
- `max_bytes` and `backup_count` have no effect unless `filename` is provided.
- Setting only `max_bytes` uses `tunning.DEFAULT_BACKUP_COUNT` and emits a warning.
- Setting only `backup_count` uses `tunning.DEFAULT_MAX_BYTES` and emits a warning.

Rotating file example:

```python
tunning.basicConfig(
    filename="app.log",
    max_bytes="10 MB",
    backup_count=5,
)
```

Useful rotation defaults:
- `tunning.DEFAULT_MAX_BYTES`: default size used when only `backup_count` is provided
- `tunning.DEFAULT_BACKUP_COUNT`: default backup count used when only `max_bytes` is provided

Defaults:
- `level=logging.WARNING`
- `filename=None`
- `max_bytes=None`
- `backup_count=None`
- `show_icon=False`
- `show_path=False`
- `show_time=False`
- `datefmt=None`
- `boxes=False`
- `rich_tracebacks=True`
- `markup=True`

`basicConfigFromYaml()` and `TunnedLogger.from_yaml()` start from
`tunning/conf.yml` and deep-merge your YAML file on top. Your config can be a
small partial override if the defaults are acceptable.

### `export()`

`export()` writes the packaged default config to a YAML file:

```python
import tunning

path = tunning.export()
```

Path behavior:
- `tunning.export()` writes `tunning.yml` next to the calling Python file.
- `tunning.export("app.yml")` writes exactly `app.yml`.
- `tunning.export("config")` writes exactly `config` if that path does not already exist as a directory.
- `tunning.export("configs/")` writes `configs/tunning.yml` if `configs` already exists as a directory.
- Missing parent directories are created automatically for explicit file paths.
- Existing files raise `FileExistsError` unless `force=True` is passed.
- The returned value is the resolved `Path` that was written.

The exported file is a full standalone config copied from packaged
`tunning/conf.yml`; it does not reconstruct the current runtime logger state.

### `levels:`

`levels:` defines metadata for built-in and custom log levels:

```yaml
levels:
  SUCCESS:
    code: 25
    symbol: '[+]'
    icon: '✅'
    style: 'green'
```

Fields:
- `code`: integer logging level code
- `symbol`: 1-3 character prefix used when icons are disabled
- `icon`: prefix used when icons are enabled
- `style`: Rich style applied to the console level prefix and message text

Built-in level names must keep stdlib codes:
- `DEBUG=10`
- `INFO=20`
- `WARNING=30`
- `ERROR=40`
- `CRITICAL=50`

Custom levels become methods on `TunnedLogger`. For example:
- `TRACE` creates `logger.trace(...)`
- `MY-CUSTOM-LEVEL` creates `logger.my_custom_level(...)`

Do not define `levels.INPUT`; prompt styling belongs in top-level `prompt:`.

### `prompt:`

`prompt:` controls `logger.prompt(...)` styling:

```yaml
prompt:
  symbol: '<<<'
  icon: '✏️'
  style: 'italic bold black on magenta'
```

Fields:
- `symbol`: 1-3 character prompt prefix used when icons are disabled
- `icon`: prompt prefix used when icons are enabled
- `style`: Rich style applied to the prompt prefix and prompt text

Prompt icon selection follows the first configured `TunnedHandler`. The spacer
after the prompt text and the user's typed answer are not styled.

### Handlers

Handlers follow stdlib `logging.config.dictConfig` syntax. `TunnedHandler`
adds one extra option:

```yaml
handlers:
  console:
    '()': 'tunning.TunnedHandler'
    level: TRACE
    log_time_format: "[%Y-%m-%d %H:%M:%S]"
    show_time: false
    show_level: true
    show_path: false
    boxes: false
    rich_tracebacks: true
    markup: true
    show_icon: false
```

`show_icon: true` switches the console prefix from `symbol` to `icon` when an
icon is configured for the level. `show_icon` is only valid on
`TunnedHandler`.

Use `log_time_format` to customize YAML-configured console timestamps. Formatter
`datefmt` is for normal formatter-driven timestamps; Rich console time rendering
uses `log_time_format` on the handler.

The console level prefix column has a minimum width of 3 terminal cells. Longer
fallback labels are not truncated and expand naturally.

Level styles apply to the console prefix, the separator before the message, and
message text only. Time and path columns stay structural, and file handlers use
plain detailed text formatting.

With `boxes: true`, each console log record is rendered in its own Rich panel.
The panel border, title, padding, and fill use the same level style as the
message. If `show_level` is enabled, the panel title contains the configured
symbol or icon plus the level name, for example `[*] INFO` or `🔵 INFO`. If
`show_time` or `show_path` are enabled, those columns stay outside the box.

### File rotation

File handlers can use normal stdlib handler classes. Parent directories are
created automatically, and human-readable `maxBytes` values are normalized:

```yaml
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    level: TRACE
    formatter: detailed
    filename: '.logs/app.log'
    maxBytes: '5 MB'
    backupCount: 3
    encoding: utf8
```

### Logger selection

Use `tunning.getLogger(name)` instead of directly instantiating loggers:

```python
import tunning

logger = tunning.getLogger(__name__)
```

`basicConfig()` and `basicConfigFromYaml()` configure the actual process root
logger. Module loggers created with `tunning.getLogger(__name__)` inherit root
handlers, matching stdlib logging practice.

`TunnedLogger.from_yaml()` is the named-logger configuration API. It configures
only the requested named logger.

If your config defines `root:`, that section is treated as the template for the
requested logger:

```yaml
root:
  level: DEBUG
  handlers: [console, file]
```

You can also configure the requested logger explicitly:

```yaml
loggers:
  my_app:
    level: INFO
    handlers: [console, file]
    propagate: false
```

Unexpected logger entries are rejected because this prototype only configures
one requested logger at a time.

## Reconfiguration rules
- Repeated `basicConfig()` and `basicConfigFromYaml()` calls do nothing unless `force=True`.
- `force=True` replaces root handlers for the basic config APIs.
- Repeated `TunnedLogger.from_yaml()` calls with the same config are idempotent.
- Repeated `TunnedLogger.from_yaml()` calls with a different config raise unless you pass `force=True`.
- `force=True` replaces handlers on the same named logger for `from_yaml()`.
- Custom level registration is process-global, so conflicting redefinitions are rejected.

## Development
Run the usage example with programmatic config:

```bash
./.venv/bin/python examples/usage.py
./.venv/bin/python examples/usage.py basic
./.venv/bin/python examples/usage.py basic --icons --paths --times --boxes
```

Run the usage example with YAML config:

```bash
./.venv/bin/python examples/usage.py pro
```

Run the usage example with zero config:

```bash
./.venv/bin/python examples/usage.py zero
```

Cheapest import smoke test:

```bash
./.venv/bin/python -c "import tunning"
```

Config smoke test:

```bash
./.venv/bin/python -c "import tunning; tunning.basicConfigFromYaml('examples/custom_logger.yml', force=True)"
```

Run the test suite:

```bash
./.venv/bin/python -m pytest
```

Run formatting, linting, and type checks:

```bash
./.venv/bin/ruff format --check .
./.venv/bin/ruff check .
./.venv/bin/mypy tunning tests
```

Install and run pre-commit hooks:

```bash
./.venv/bin/pre-commit install
./.venv/bin/pre-commit run --all-files
```

Run one focused test:

```bash
./.venv/bin/python -m pytest tests/test_tunned_logger.py -k prompt
```
