# tunning

`tunning` is a small but stylish Python logging helper for CLI applications.
It builds on stdlib `logging` and Rich to provide readable terminal logs,
rotating file logs, YAML configuration, custom levels, and a styled prompt
helper without wrapping your CLI or TUI framework.

## Features

- Colored console output through `TunnedHandler`
- Stdlib-like root logger configuration through `basicConfig()`
- YAML-driven configuration with packaged defaults
- Rotating file logs through stdlib handlers
- Custom levels such as `TRACE` and `SUCCESS`
- Styled interactive prompts through `logger.prompt(...)`
- Optional boxed console records with Rich panels

> Optional extras are available for CLI and TUI integrations, but `tunning` does not wrap Typer or Textual.

## Install

```bash
pip install tunning
```

For local development:

```bash
git clone https://github.com/octanima-labs/tunning
cd tunning
pip install -e ".[dev,cli,tui,docs]"
```

## Quick Start

```python
import tunning

logger = tunning.getLogger(__name__)

logger.info("application started")
logger.success("everything looks good")

name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

This zero-config path installs packaged console defaults lazily on first use.
Configure logging explicitly when you want predictable startup behavior:

```python
import tunning

tunning.basicConfig(
    level="INFO",
    show_time=True,
    datefmt=tunning.ISO_FORMAT,
)

logger = tunning.getLogger(__name__)
logger.info("configured output")
```

## Files And YAML

Use a file handler:

```python
tunning.basicConfig(filename="app.log", level="INFO")
```

Use rotating file logs:

```python
tunning.basicConfig(
    filename="app.log",
    max_bytes="10 MB",
    backup_count=5,
)
```

Export a full starter YAML config into your project:

```python
import tunning

config_path = tunning.export()
```

Load YAML configuration:

```python
tunning.basicConfigFromYaml("tunning.yml", force=True)
```

## Documentation

- [Quick Start](https://octanima-labs.github.io/tunning/quick-start/)
- [Configuration](https://octanima-labs.github.io/tunning/configuration/)
- [Examples](https://octanima-labs.github.io/tunning/examples/)
- [API Reference](https://octanima-labs.github.io/tunning/api/)
- [Development](https://octanima-labs.github.io/tunning/development/)

## Development

Common contributor commands and documentation build steps live in
[Development](https://octanima-labs.github.io/tunning/development/).

The short version:

```bash
./.venv/bin/python -m pytest
./.venv/bin/ruff check .
./.venv/bin/mypy tunning tests
./.venv/bin/mkdocs build --strict
```

## License

`tunning` is distributed under the MIT license.
