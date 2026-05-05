# tuning

![library icon](./docs/icon.png)

`tuning` is a small but stylish Python logging helper for CLI applications.
It builds on stdlib `logging` and Rich to provide readable terminal logs,
rotating file logs, YAML configuration, custom levels, and a styled prompt
helper without wrapping your CLI or TUI framework.

## Features

- Colored console output through `TunedHandler`
- Stdlib-like root logger configuration through `basicConfig()`
- YAML-driven configuration with packaged defaults
- Rotating file logs through stdlib handlers
- Custom levels such as `TRACE` and `SUCCESS`
- Styled interactive prompts through `logger.prompt(...)`
- Custom app banners through `banner(...)`
- Optional boxed console records with Rich panels

> Optional extras are available for CLI and TUI integrations, but `tuning` does not wrap Typer or Textual.

## Install

```bash
pip install tuning
```

For local development:

```bash
git clone https://github.com/octanima-labs/tuning
cd tuning
pip install -e ".[dev,cli,tui,docs]"
```

## Quick Start

```python
import tuning

logger = tuning.getLogger(__name__)

logger.info("application started")
logger.success("everything looks good")

name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

This zero-config path installs packaged console defaults lazily on first use.
Configure logging explicitly when you want predictable startup behavior:

```python
import tuning

tuning.basicConfig(
    level="INFO",
    show_time=True,
    datefmt=tuning.ISO_FORMAT,
)

logger = tuning.getLogger(__name__)
logger.info("configured output")
```

Use `show_level=False` when console output should contain only the message.

Add a runtime-only custom level:

```python
tuning.addLevel(7, "MY_CUSTOM_LEVEL", symbol="MC", style="bright_blue")

logger = tuning.getLogger(__name__)
logger.my_custom_level("custom runtime output")
```

Print a custom app banner from `banners.txt`:

```python
import tuning

tuning.banner()
```

With no path, `banner()` searches upward from the calling file for
`banners.txt`. Each section starts with a strict lowercase marker such as
`### ansi_shadow`.

Customize rendering with Rich styles:

```python
tuning.banner(
    name="ansi_shadow",
    border_style="bright_cyan",
    text_style="bold bright_magenta",
    background_style="on black",
    padding=(0, 2),
    box="HEAVY",
)
```

## Files And YAML

Use a file handler:

```python
tuning.basicConfig(filename="app.log", level="INFO")
```

Use rotating file logs:

```python
tuning.basicConfig(
    filename="app.log",
    max_bytes="10 MB",
    backup_count=5,
)
```

Export a full starter YAML config into your project:

```python
import tuning

config_path = tuning.export()
```

Load YAML configuration:

```python
tuning.basicConfigFromYaml("tuning.yml", force=True)
```

## Documentation

- [Quick Start](https://octanima-labs.github.io/tuning/quick-start/)
- [Configuration](https://octanima-labs.github.io/tuning/configuration/)
- [Examples](https://octanima-labs.github.io/tuning/examples/)
- [API Reference](https://octanima-labs.github.io/tuning/api/)
- [Development](https://octanima-labs.github.io/tuning/development/)

## Development

Common contributor commands and documentation build steps live in
[Development](https://octanima-labs.github.io/tuning/development/).

The short version:

```bash
./.venv/bin/python -m pytest
./.venv/bin/ruff check .
./.venv/bin/mypy tuning tests
./.venv/bin/sphinx-build -W -b dirhtml docs site
```

## License

`tuning` is distributed under the MIT license.
