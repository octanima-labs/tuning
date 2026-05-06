# Tuned logging

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item}
```{image} ./logo.png
:alt: tuning logo
:class: dark-light
:width: 300px
```
:::

:::{grid-item}
```{image} ./title_logo_nav.png
:alt: tuning banner
:class: dark-light
:width: 300px
:::

::::

**Colorful and customizable dual-logging** module for CLI applications. Emojis included 😉.

The idea is simple, display **human-readable and colorful terminal** logs, while keeping **file** logs **detailed** and sober.

It builds on [stdlib _logging_](https://docs.python.org/3/library/logging.html) and [_Rich_](https://github.com/textualize/rich), so you can use it as usual:
- logging via named functions: `logger.my_custom_lvl()`
- natural language defined styles: `bold italic white on red`

## Index

- [Quick Start](quick-start.md): basic setup and first log messages.
- [Configuration](configuration.md): programmatic and YAML configuration notes.
- [Examples](examples.md): practical snippets.
- [API Reference](api): generated from public source docstrings.
- [Development](development.md): contributor commands and checks.

```{toctree}
:maxdepth: 2
:caption: Contents

quick-start
configuration
examples
api
development
```
