# AGENTS.md

## Repo Shape
- This is an early Python package prototype with package metadata in `pyproject.toml`.
- The distribution name is `tunning` and the import package is `tunning`.
- Project code lives in `./tunning/logger.py`. The two public classes are `TunnedLogger` and `TunnedHandler`.
- Packaged defaults live in `./tunning/conf.yml`. Repository config examples live in `examples/`.
- There is no CLI entrypoint. The real runtime entrypoint is `TunnedLogger.from_yaml(...)`.
- Examples live in `examples/`. They are not part of the public API.

## Naming conventions
- The distribution name is `tunning`.
- The import package is `tunning`.
- The main runtime entrypoint is `TunnedLogger.from_yaml(...)`.
- The implementation lives in `tunning/logger.py`.
- Runnable examples live in `examples/`.
- The project is MIT licensed.

## Commands
- Use the repo-local interpreter: `./.venv/bin/python`.
- Install deps with `./.venv/bin/pip install -r requirements.txt`.
- Cheapest import smoke test: `./.venv/bin/python -c "import tunning"`.
- Verified config smoke test: `./.venv/bin/python -c "from tunning import TunnedLogger; TunnedLogger.from_yaml('examples/custom_logger.yml', name='smoke', force=True)"`.
- Test suite: `./.venv/bin/python -m pytest`.
- Focus one test: `./.venv/bin/python -m pytest tests/test_tunned_logger.py -k prompt`.
- Format check: `./.venv/bin/ruff format --check .`.
- Lint: `./.venv/bin/ruff check .`.
- Type check: `./.venv/bin/mypy tunning tests`.
- Pre-commit: `./.venv/bin/pre-commit run --all-files`.
- Basic example: `./.venv/bin/python examples/basic_usage.py`.

## Distribution

- Do not rebuild distributable `egg` on every change on the code. Wait until the user requests it explicitly.

## Logging Flow
- `TunnedLogger.from_yaml()` loads `tunning/conf.yml` as defaults and deep-merges the provided YAML override on top. `examples/custom_logger.yml` is intentionally a partial override, not a standalone full config.
- Top-level `prompt:` is separate from `levels:`. Do not model prompt styling as a fake `INPUT` log level.
- Built-in levels must keep stdlib codes: `DEBUG=10`, `INFO=20`, `WARNING=30`, `ERROR=40`, `CRITICAL=50`. Use `WARNING`, not `WARN`.
- Custom levels become dynamic methods on `TunnedLogger` such as `trace()` and `success()`.
- `from_yaml()` configures only the requested named logger. If the YAML only defines `root:`, that section is treated as the template for the named logger; it does not configure the actual process root logger.
- File handler parent directories and human-readable `maxBytes` values are normalized in `tunning/logger.py`, not in the YAML itself.
- The custom level registry is process-global. `force=True` can reconfigure handlers for the same logger, but conflicting level redefinitions should be treated as a design problem, not worked around.

## Coordination
- If you touch logging behavior, update `./tunning/logger.py`, `./tunning/conf.yml`, and `tests/test_tunned_logger.py` together.
- If you change public behavior or project direction, update `README.md`, `DESIGN.md`, and this file when relevant.
- The current roadmap priority is stabilization: add tests around existing behavior before adding new features.
- Packaging metadata and editable install behavior have been verified; docs URLs are still pending.
- Quality gates use pytest, Ruff, mypy, pre-commit, and GitHub Actions across Python 3.11 through 3.14.

## Doc Reliability
- `README.md` is the user-facing usage guide.
- `DESIGN.md` contains current architecture notes and the roadmap, but the code and YAML files are the source of truth for runtime behavior.
- Runtime behavior is still defined by `./tunning/logger.py`, `./tunning/conf.yml`, and tests. When docs conflict with implementation, trust implementation and update the stale docs.
- There is no CLI wrapper.

## Roadmap
- Stabilize current behavior with more pytest coverage before adding features.
- Keep linting, formatting, type checking, and tests passing before adding features.
- Keep prompt styling separate from log levels. Do not reintroduce `levels.INPUT`.
- Keep custom level registration strict because stdlib logging level names and codes are process-global.
- Keep examples under `examples/`, not under the package directory.
- Future features such as `message_color` and `boxes` belong after stabilization.
- Do not add a `Typer` wrapper. `typer` is an optional `cli` extra; this library stays focused on logging.
- Do not add a `Textual` abstraction. `textual` is an optional `tui` extra.
