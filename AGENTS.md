# AGENTS.md

## Repo Shape
- This is an early Python package prototype with package metadata in `pyproject.toml`.
- The distribution name is `tuning` and the import package is `tuning`.
- Project code lives in `./tuning/logger.py`. The two public classes are `TunedLogger` and `TunedHandler`.
- Packaged defaults live in `./tuning/conf.yml`. Repository config examples live in `examples/`.
- There is no CLI entrypoint. The preferred runtime entrypoints are `tuning.getLogger(...)`, `tuning.basicConfig(...)`, `tuning.basicConfigFromYaml(...)`, `tuning.export(...)`, and `tuning.banner(...)`.
- Examples live in `examples/`. They are not part of the public API.

## Naming conventions
- The distribution name is `tuning`.
- The import package is `tuning`.
- The main runtime entrypoints are `tuning.getLogger(...)`, `tuning.basicConfig(...)`, `tuning.basicConfigFromYaml(...)`, `tuning.export(...)`, and `tuning.banner(...)`.
- The implementation lives in `tuning/logger.py`.
- Runnable examples live in `examples/`.
- Sample app banners live in `examples/banners.txt`.
- The project is MIT licensed.

## Commands
- Use the repo-local interpreter: `./.venv/bin/python`.
- Install deps with `./.venv/bin/pip install -r requirements.txt`.
- Cheapest import smoke test: `./.venv/bin/python -c "import tuning"`.
- Verified config smoke test: `./.venv/bin/python -c "import tuning; tuning.basicConfigFromYaml('examples/custom_logger.yml', force=True)"`.
- Test suite: `./.venv/bin/python -m pytest`.
- Focus one test: `./.venv/bin/python -m pytest tests/test_tuned_logger.py -k prompt`.
- Format check: `./.venv/bin/ruff format --check .`.
- Lint: `./.venv/bin/ruff check .`.
- Type check: `./.venv/bin/mypy tuning tests`.
- Docs build: `./.venv/bin/sphinx-build -W -b dirhtml docs site` after installing `.[docs]`.
- Pre-commit: `./.venv/bin/pre-commit run --all-files`.
- Basic example: `./.venv/bin/python examples/usage.py`.

## Documentation

Public API docs are generated from source docstrings with Sphinx autodoc. Keep
public docstrings current when changing public APIs.

The generated site output is written to `site/`, which is ignored by git.


## Distribution

- Do not rebuild distributable `egg` on every change on the code. Wait until the user requests it explicitly.

## Logging Flow
- `basicConfigFromYaml()` and `TunedLogger.from_yaml()` load `tuning/conf.yml` as defaults and deep-merge the provided YAML override on top. `examples/custom_logger.yml` is intentionally a partial override, not a standalone full config.
- `basicConfigFromYaml()` with no path loads the packaged `tuning/conf.yml` defaults directly.
- `tuning.export(...)` writes the packaged `tuning/conf.yml` text as a full standalone YAML file; it does not reconstruct live runtime logger state.
- Top-level `prompt:` is separate from `levels:`. Do not model prompt styling as a fake `INPUT` log level.
- Built-in levels must keep stdlib codes: `DEBUG=10`, `INFO=20`, `WARNING=30`, `ERROR=40`, `CRITICAL=50`. Use `WARNING`, not `WARN`.
- Custom levels become dynamic methods on `TunedLogger` such as `trace()` and `success()`.
- `addLevel(...)` registers custom levels for the current process only, using the same strict global registry and dynamic method rules as YAML custom levels. It does not mutate YAML files or exported defaults.
- Level styles always apply to console level prefixes, the separator before the message, and the full message text. There is no `message_color` opt-out. Prompt styles apply to the rendered prompt prefix and question text only; the trailing input spacer, user's answer, time/path columns, and file handlers are not styled by level metadata.
- The console level prefix column has a minimum width of 3 terminal cells; longer fallback labels expand naturally.
- `basicConfig()` and `basicConfigFromYaml()` configure the actual process root logger and let named child loggers inherit handlers.
- Using a `TunedLogger` before explicit configuration lazily installs packaged level metadata and a console-only root handler at INFO level. Do not replace existing root handlers during zero config.
- `basicConfig(filename=...)` is file-only; use `basicConfig(filename=..., console=True)` for console plus file. Console options (`show_icon`, `show_level`, `show_path`, `show_time`, `boxes`, `rich_tracebacks`, `markup`) do not affect file handlers.
- `basicConfig(filename=..., max_bytes=..., backup_count=...)` uses `RotatingFileHandler`. If only one rotation option is provided, the missing value defaults to `DEFAULT_MAX_BYTES` or `DEFAULT_BACKUP_COUNT` with a warning. Rotation options are ignored when `filename` is omitted.
- `boxes=True` renders each console log record in its own Rich panel. The panel border, title, padding, and fill use the level style; time/path columns stay outside the panel; tracebacks render inside the same panel; consecutive records are not grouped.
- `from_yaml()` configures only the requested named logger. If the YAML only defines `root:`, that section is treated as the template for the named logger; it does not configure the actual process root logger.
- File handler parent directories and human-readable `maxBytes` values are normalized in `tuning/logger.py`, not in the YAML itself.
- The custom level registry is process-global. `force=True` can reconfigure handlers for the same logger, but conflicting level redefinitions should be treated as a design problem, not worked around.

## Coordination
- If you touch logging behavior, update `./tuning/logger.py`, `./tuning/conf.yml`, and `tests/test_tuned_logger.py` together.
- If you change public behavior or project direction, update `README.md`, `DESIGN.md`, and this file when relevant.
- The current runtime roadmap is stabilized for this prototype pass. Treat grouped boxes as a follow-up feature, not current implementation scope.
- Packaging metadata and editable install behavior have been verified; docs URLs are a packaging follow-up, not a runtime gap.
- Quality gates use pytest, Ruff, mypy, pre-commit, and GitHub Actions across Python 3.11 through 3.14.
- Public API docs are generated with Sphinx autodoc from source docstrings. Keep docstrings current when changing public APIs.

## Doc Reliability
- `README.md` is the user-facing usage guide.
- `DESIGN.md` contains current architecture notes and the roadmap, but the code and YAML files are the source of truth for runtime behavior.
- Runtime behavior is still defined by `./tuning/logger.py`, `./tuning/conf.yml`, and tests. When docs conflict with implementation, trust implementation and update the stale docs.
- There is no CLI wrapper.

## Roadmap
- Stabilization pass is complete for the current prototype; keep adding pytest coverage around behavior changes.
- Keep linting, formatting, type checking, and tests passing before adding features.
- Keep prompt styling separate from log levels. Do not reintroduce `levels.INPUT`.
- Keep custom level registration strict because stdlib logging level names and codes are process-global.
- Keep `addLevel()` runtime-only; do not persist programmatic levels back into YAML or `export()` output.
- Keep examples under `examples/`, not under the package directory.
- The remaining follow-up for boxes is optional grouping of consecutive records from the same level.
- Do not add a `Typer` wrapper. `typer` is an optional `cli` extra; this library stays focused on logging.
- Do not add a `Textual` abstraction. `textual` is an optional `tui` extra.
