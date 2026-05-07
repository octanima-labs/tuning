# Quick Start

Install the package:

```bash
pip install 2ning
```

Create a logger and write messages:

```python
import tuning

logger = tuning.getLogger(__name__)

logger.info("application started")
logger.success("everything looks good")
```

Calling a logger before explicit configuration installs console-only defaults
lazily. Configure the root logger explicitly when you want predictable startup
behavior:

```python
import tuning

tuning.basicConfig(level="INFO", show_time=True, datefmt=tuning.ISO_FORMAT)

logger = tuning.getLogger(__name__)
logger.info("configured output")
```

Export a full starter YAML config:

```python
import tuning

config_path = tuning.export()
```

With no path, `export()` writes `tuning.yml` next to the Python file that
called it.

Print an app banner from a nearby `banners.txt` file:

```python
import tuning

tuning.banner()
```

When styles are omitted, `banner()` picks random bold colors for the text and
border. Pass Rich style strings, `background_style=...`, `box=...`,
`padding=...`, or `border=False` to customize the rendering.
