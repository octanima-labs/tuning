# Configuration

`tunning` supports two primary configuration paths: programmatic root logger
configuration with `basicConfig()` and YAML configuration with
`basicConfigFromYaml()`.

## How Configuration Works

- `tunning.basicConfig()` configures the actual process root logger, like `logging.basicConfig()`.
- Calling logger methods before explicit configuration installs console-only zero-config defaults.
- Repeated `basicConfig()` and `basicConfigFromYaml()` calls do nothing unless `force=True`.
- `basicConfigFromYaml()` loads packaged defaults from `tunning/conf.yml` first.
- The YAML file you pass in is deep-merged on top of packaged defaults.
- `basicConfigFromYaml()` preserves `root:` as the real process root logger config.
- `examples/custom_logger.yml` is intentionally a partial override, not a standalone full config.
- `tunning.export(...)` writes the packaged default config as a full standalone YAML file.

## Programmatic Configuration

Console output:

```python
import tunning

tunning.basicConfig(
    level="INFO",
    show_time=True,
    datefmt=tunning.ISO_FORMAT,
    show_icon=True,
)
```

File output:

```python
import tunning

tunning.basicConfig(filename="app.log", level="INFO")
```

Console and file output together:

```python
tunning.basicConfig(
    filename="app.log",
    console=True,
    level="INFO",
    show_icon=True,
)
```

Rotating file output:

```python
tunning.basicConfig(
    filename="app.log",
    level="INFO",
    max_bytes="10 MB",
    backup_count=5,
)
```

`basicConfig(filename=...)` is file-only. Use
`basicConfig(filename=..., console=True)` for console plus file.

`max_bytes` and `backup_count` are ignored when `filename` is omitted. If only
one rotation option is provided, the other uses `DEFAULT_MAX_BYTES` or
`DEFAULT_BACKUP_COUNT` and emits a warning.

Useful constants:

- `tunning.ISO_FORMAT`: `[%Y-%m-%d %H:%M:%S]`
- `tunning.DEFAULT_MAX_BYTES`: default size used when only `backup_count` is provided
- `tunning.DEFAULT_BACKUP_COUNT`: default backup count used when only `max_bytes` is provided

## YAML Configuration

Generate a full starter config:

```python
import tunning

tunning.export("tunning.yml")
```

Load the YAML config:

```python
import tunning

tunning.basicConfigFromYaml("tunning.yml", force=True)
```

`basicConfigFromYaml()` with no path loads only the packaged default config.

The exported YAML is copied from packaged `tunning/conf.yml`; it does not
reconstruct live runtime logger state.

## `export()`

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

## `levels:`

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
- `symbol`: compact prefix used when icons are disabled
- `icon`: prefix used when icons are enabled
- `style`: Rich style applied to console level prefixes and message text

Built-in levels must keep stdlib codes: `DEBUG=10`, `INFO=20`, `WARNING=30`,
`ERROR=40`, and `CRITICAL=50`. Use `WARNING`, not `WARN`. Use `CRITICAL`, not
`FATAL`.

Custom levels become methods on `TunnedLogger`. For example, `TRACE` creates
`logger.trace(...)`, and `MY-CUSTOM-LEVEL` creates
`logger.my_custom_level(...)`.

Do not define `levels.INPUT`; prompt styling belongs in top-level `prompt:`.

## `prompt:`

`prompt:` controls `logger.prompt(...)` styling:

```yaml
prompt:
  symbol: '<<<'
  icon: '✏️'
  style: 'italic bold black on magenta'
```

Prompt icon selection follows the first configured `TunnedHandler`. The spacer
after the prompt text and the user's typed answer are not styled.

## Handler Options

Handlers follow stdlib `logging.config.dictConfig` syntax. `TunnedHandler` adds
console-specific options:

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
icon is configured for the level. `show_icon` is only valid on `TunnedHandler`.

Use `log_time_format` to customize YAML-configured console timestamps. Formatter
`datefmt` is for normal formatter-driven timestamps; Rich console time rendering
uses `log_time_format` on the handler.

The console level prefix column has a minimum width of 3 terminal cells. Longer
fallback labels are not truncated and expand naturally.

Level styles apply to the console prefix, the separator before the message, and
message text. Time and path columns stay structural, and file handlers use plain
detailed text formatting.

With `boxes: true`, each console log record is rendered in its own Rich panel.
The panel border, title, padding, and fill use the same level style as the
message. If `show_level` is enabled, the panel title contains the configured
symbol or icon plus the level name. If `show_time` or `show_path` are enabled,
those columns stay outside the box.

## File Rotation In YAML

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

## Logger Selection

Use `tunning.getLogger(name)` instead of directly instantiating loggers:

```python
import tunning

logger = tunning.getLogger(__name__)
```

`basicConfig()` and `basicConfigFromYaml()` configure the actual process root
logger. Module loggers created with `tunning.getLogger(__name__)` inherit root
handlers, matching stdlib logging practice.

`TunnedLogger.from_yaml()` configures only the requested named logger. If the
YAML only defines `root:`, that section is treated as the template for the named
logger and does not configure the actual process root logger.

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

## Reconfiguration Rules

- Repeated `basicConfig()` and `basicConfigFromYaml()` calls do nothing unless `force=True`.
- `force=True` replaces root handlers for the basic config APIs.
- Repeated `TunnedLogger.from_yaml()` calls with the same config are idempotent.
- Repeated `TunnedLogger.from_yaml()` calls with a different config raise unless you pass `force=True`.
- `force=True` replaces handlers on the same named logger for `from_yaml()`.
- Custom level registration is process-global, so conflicting redefinitions are rejected.
