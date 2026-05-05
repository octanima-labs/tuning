# Examples

The runnable demo script in the repository lives at `examples/usage.py`.


## Console And File Output

```python
import tuning

tuning.basicConfig(
    filename="app.log",
    console=True,
    level="INFO",
    show_time=True,
    datefmt=tuning.ISO_FORMAT,
)

logger = tuning.getLogger(__name__)
logger.info("application started")
```

## Rotating File Logs

```python
import tuning

tuning.basicConfig(
    filename="app.log",
    level="INFO",
    max_bytes="10 MB",
    backup_count=5,
)

logger = tuning.getLogger(__name__)
logger.info("rotating file output")
```

## Boxed Console Records

```python
import tuning

tuning.basicConfig(level="INFO", boxes=True, show_icon=True)

logger = tuning.getLogger(__name__)
logger.success("boxed output")
```

## Styled Prompt

```python
import tuning

logger = tuning.getLogger(__name__)
name = logger.prompt("Your name?")
logger.info("hello %s", name)
```

## App Banner

Create a `banners.txt` file in your project:

```text
### compact
TUNING
```

Print a named banner, or omit `name` to select a random banner that fits the
terminal width:

```python
import tuning

tuning.banner(name="compact")
```

Customize the Rich panel style, background, box, padding, or remove the border:

```python
import tuning

tuning.banner(
    name="compact",
    border_style="bright_cyan",
    text_style="bold bright_magenta",
    background_style="on black",
    padding=(0, 2),
    box="HEAVY",
)

tuning.banner(name="compact", border=False, padding=(1, 4))
```

## YAML Configuration

Export a full starter config:

```python
import tuning

tuning.export("tuning.yml")
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
import tuning

tuning.basicConfigFromYaml("tuning.yml", force=True)

logger = tuning.getLogger(__name__)
logger.info("configured from YAML")
```
