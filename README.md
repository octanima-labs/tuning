# tunning

`tunning` is a small but stylish Python logging helper for CLI apps.

It builds on stdlib `logging` and `rich` to give you:
- colored console output through `TunnedHandler`
- rotating file logs through normal `logging` handlers
- YAML-driven configuration
- custom levels such as `TRACE` and `SUCCESS`
- a styled `prompt()` helper for interactive CLI input

> Optional extras are available for CLI and TUI integrations, but `tunning` does not wrap Typer or Textual.

## Install
Use the repo-local virtualenv:

```bash
./.venv/bin/pip install -r requirements.txt
```

`requirements.txt` is the full developer dependency set. For package installs,
use extras when you need optional integrations:

```bash
pip install "tunning[cli]"
pip install "tunning[tui]"
pip install "tunning[cli,tui]"
```

Project metadata lives in `pyproject.toml`. Build tooling is included in the
`dev` extra and in `requirements.txt`.

## Quick start

```python
from tunning import TunnedLogger

logger = TunnedLogger.from_yaml(
    "examples/custom_logger.yml",
    name="demo",
    force=True,
)

logger.trace("loading configuration")
logger.info("application started")
logger.success("everything looks good")

name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

## How configuration works
- `TunnedLogger.from_yaml()` always loads the packaged default config from `tunning/conf.yml` first.
- The YAML file you pass in is deep-merged on top of those defaults.
- `examples/conf.yml` shows a full config with the same shape as the packaged defaults.
- `examples/custom_logger.yml` is intentionally a partial override, not a standalone full config.
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

`TunnedLogger.from_yaml()` starts from `tunning/conf.yml` and deep-merges your
YAML file on top. Your config can be a small partial override if the defaults are
acceptable.

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
- `style`: Rich style applied to the rendered level prefix

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
- `style`: Rich style applied to the prompt prefix

Prompt icon selection follows the first configured `TunnedHandler`.

### Handlers

Handlers follow stdlib `logging.config.dictConfig` syntax. `TunnedHandler`
adds one extra option:

```yaml
handlers:
  console:
    '()': 'tunning.TunnedHandler'
    level: TRACE
    show_time: false
    show_level: true
    show_path: false
    rich_tracebacks: true
    markup: true
    show_icon: false
```

`show_icon: true` switches the console prefix from `symbol` to `icon` when an
icon is configured for the level. `show_icon` is only valid on
`TunnedHandler`.

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

`from_yaml()` configures only the requested named logger.

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
- Repeated calls with the same config are idempotent.
- Repeated calls with a different config raise unless you pass `force=True`.
- `force=True` replaces handlers on the same named logger.
- Custom level registration is process-global, so conflicting redefinitions are rejected.

## Development
Run the basic example:

```bash
./.venv/bin/python examples/basic_usage.py
```

Cheapest import smoke test:

```bash
./.venv/bin/python -c "import tunning"
```

Config smoke test:

```bash
./.venv/bin/python -c "from tunning import TunnedLogger; TunnedLogger.from_yaml('examples/custom_logger.yml', name='smoke', force=True)"
```

Run the test suite:

```bash
./.venv/bin/python -m pytest
```

Run one focused test:

```bash
./.venv/bin/python -m pytest tests/test_tunned_logger.py -k prompt
```
