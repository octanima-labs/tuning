# Examples

## Console And File Output

```python
import tunning

tunning.basicConfig(
    filename="app.log",
    console=True,
    level="INFO",
    show_time=True,
    datefmt=tunning.ISO_FORMAT,
)

logger = tunning.getLogger(__name__)
logger.info("application started")
```

## Rotating File Logs

```python
import tunning

tunning.basicConfig(
    filename="app.log",
    level="INFO",
    max_bytes="10 MB",
    backup_count=5,
)

logger = tunning.getLogger(__name__)
logger.info("rotating file output")
```

## Boxed Console Records

```python
import tunning

tunning.basicConfig(level="INFO", boxes=True, show_icon=True)

logger = tunning.getLogger(__name__)
logger.success("boxed output")
```

## Styled Prompt

```python
import tunning

logger = tunning.getLogger(__name__)
name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

## YAML Configuration

Export a full starter config:

```python
import tunning

tunning.export("tunning.yml")
```

Use a small override file:

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

Load YAML configuration:

```python
import tunning

tunning.basicConfigFromYaml("tunning.yml", force=True)

logger = tunning.getLogger(__name__)
logger.info("configured from YAML")
```

The runnable demo script in the repository lives at `examples/usage.py`.
