# Development

Clone the repository and install development dependencies:

```bash
git clone https://github.com/octanima-labs/tuning
cd tuning
pip install -e ".[dev,cli,tui,docs]"
```

Use the repo-local interpreter when working in this checkout:

```bash
./.venv/bin/python -c "import tuning"
```

## Smoke Tests

Cheapest import smoke test:

```bash
./.venv/bin/python -c "import tuning"
```

Config smoke test:

```bash
./.venv/bin/python -c "import tuning; tuning.basicConfigFromYaml('examples/custom_logger.yml', force=True)"
```

Run the usage example with programmatic config:

```bash
./.venv/bin/python examples/usage.py
./.venv/bin/python examples/usage.py basic
./.venv/bin/python examples/usage.py basic --icons --paths --times --boxes
```

Run the usage example with YAML config:

```bash
./.venv/bin/python examples/usage.py pro
```

Run the usage example with zero config:

```bash
./.venv/bin/python examples/usage.py zero
```

## Quality Gates

Run the test suite:

```bash
./.venv/bin/python -m pytest
```

Run one focused test:

```bash
./.venv/bin/python -m pytest tests/test_tuned_logger.py -k prompt
```

Run formatting, linting, and type checks:

```bash
./.venv/bin/ruff format --check .
./.venv/bin/ruff check .
./.venv/bin/mypy tuning tests
```

Build documentation:

```bash
./.venv/bin/mkdocs build --strict
```

Run pre-commit hooks:

```bash
./.venv/bin/pre-commit install
./.venv/bin/pre-commit run --all-files
```
