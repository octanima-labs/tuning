# Quick Start

Install the package:

```bash
pip install tunning
```

Create a logger and write messages:

```python
import tunning

logger = tunning.getLogger(__name__)

logger.info("application started")
logger.success("everything looks good")
```

Calling a logger before explicit configuration installs console-only defaults
lazily. Configure the root logger explicitly when you want predictable startup
behavior:

```python
import tunning

tunning.basicConfig(level="INFO", show_time=True, datefmt=tunning.ISO_FORMAT)

logger = tunning.getLogger(__name__)
logger.info("configured output")
```

Export a full starter YAML config:

```python
import tunning

config_path = tunning.export()
```

With no path, `export()` writes `tunning.yml` next to the Python file that
called it.
