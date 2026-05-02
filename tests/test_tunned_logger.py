from __future__ import annotations

import logging
import uuid
from pathlib import Path

import bitmath
import pytest
import yaml

import tunning.logger as tunning_module
from tunning import TunnedHandler, TunnedLogger


def _write_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf8") as file_handle:
        yaml.safe_dump(data, file_handle, sort_keys=False)


def _write_empty_defaults(path: Path) -> None:
    _write_yaml(path, {})


def _unique_level_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}".upper()


def _unique_level_code() -> int:
    return 1000 + (uuid.uuid4().int % 1_000_000)


def _drop_logger(name: str) -> None:
    manager = logging.getLogger().manager
    logger = manager.loggerDict.pop(name, None)
    if isinstance(logger, logging.Logger):
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def _console_handler(logger: logging.Logger) -> TunnedHandler:
    for handler in logger.handlers:
        if isinstance(handler, TunnedHandler):
            return handler
    raise AssertionError("Expected a TunnedHandler")


def _file_handler(logger: logging.Logger) -> logging.Handler:
    for handler in logger.handlers:
        if hasattr(handler, "baseFilename"):
            return handler
    raise AssertionError("Expected a file handler")


@pytest.fixture
def logger_name() -> str:
    name = f"tests.{uuid.uuid4().hex}"
    yield name
    _drop_logger(name)


def test_from_yaml_returns_tunned_logger_and_registers_levels(
    tmp_path: Path,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "app.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "handlers": {
                "console": {"show_icon": False, "level": "CRITICAL"},
                "file": {"filename": str(log_path)},
            },
            "root": {"level": "TRACE"},
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, force=True)

    assert isinstance(logger, TunnedLogger)
    assert hasattr(logger, "trace")
    assert logger.propagate is False
    assert logging.getLevelName(5) == "TRACE"

    file_handler = _file_handler(logger)
    assert getattr(file_handler, "maxBytes") == int(bitmath.parse_string("5 MB").bytes)
    assert log_path.parent.exists()
    assert log_path.exists()

    logger.trace("trace message")


def test_prompt_uses_the_first_handler_show_icon_setting(
    tmp_path: Path,
    logger_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "logs" / "app.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "handlers": {
                "console": {"show_icon": True},
                "file": {"filename": str(log_path)},
            }
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, force=True)
    handler = _console_handler(logger)
    captured: dict[str, object] = {}

    def fake_input(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "typed value"

    monkeypatch.setattr(handler.console, "input", fake_input)

    value = logger.prompt("Enter a value")

    assert value == "typed value"
    assert "✏️" in captured["prompt"].plain
    assert "Enter a value" in captured["prompt"].plain
    assert captured["kwargs"]["markup"] is False
    assert captured["kwargs"]["password"] is False


def test_invalid_builtin_level_code_raises_a_clear_error(
    tmp_path: Path,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "app.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "levels": {
                "DEBUG": {"code": 20},
            },
            "handlers": {
                "file": {"filename": str(log_path)},
            },
        },
    )

    with pytest.raises(ValueError, match="Built-in level DEBUG"):
        TunnedLogger.from_yaml(config_path, name=logger_name, force=True)


def test_from_yaml_is_idempotent_and_force_reconfigures(
    tmp_path: Path,
    logger_name: str,
) -> None:
    log_path_one = tmp_path / "logs-one" / "app.log"
    log_path_two = tmp_path / "logs-two" / "app.log"
    config_path_one = tmp_path / "logger-one.yml"
    config_path_two = tmp_path / "logger-two.yml"
    _write_yaml(
        config_path_one,
        {
            "handlers": {
                "console": {"show_icon": False},
                "file": {"filename": str(log_path_one)},
            }
        },
    )
    _write_yaml(
        config_path_two,
        {
            "handlers": {
                "console": {"show_icon": True},
                "file": {"filename": str(log_path_two)},
            }
        },
    )

    logger = TunnedLogger.from_yaml(config_path_one, name=logger_name, force=True)
    same_logger = TunnedLogger.from_yaml(config_path_one, name=logger_name)
    assert logger is same_logger

    with pytest.raises(ValueError, match="different config"):
        TunnedLogger.from_yaml(config_path_two, name=logger_name)

    reconfigured_logger = TunnedLogger.from_yaml(
        config_path_two,
        name=logger_name,
        force=True,
    )
    assert logger is reconfigured_logger
    assert _console_handler(reconfigured_logger).show_icon is True
    assert Path(getattr(_file_handler(reconfigured_logger), "baseFilename")) == log_path_two.resolve()


def test_existing_standard_logger_name_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "app.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "handlers": {
                "file": {"filename": str(log_path)},
            }
        },
    )

    standard_logger = logging.getLogger(logger_name)
    assert not isinstance(standard_logger, TunnedLogger)

    with pytest.raises(ValueError, match="expected TunnedLogger"):
        TunnedLogger.from_yaml(config_path, name=logger_name, force=True)


def test_partial_override_deep_merges_with_defaults(
    tmp_path: Path,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "merged.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "handlers": {
                "console": {
                    "level": "ERROR",
                    "show_icon": True,
                },
                "file": {"filename": str(log_path)},
            },
            "root": {"level": "ERROR"},
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, force=True)

    console_handler = _console_handler(logger)
    file_handler = _file_handler(logger)
    assert logger.level == logging.ERROR
    assert console_handler.level == logging.ERROR
    assert console_handler.show_icon is True
    assert console_handler.markup is True
    assert getattr(file_handler, "maxBytes") == int(bitmath.parse_string("5 MB").bytes)
    assert getattr(file_handler, "backupCount") == 3


def test_custom_level_conflict_by_name_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path_one = tmp_path / "logger-one.yml"
    config_path_two = tmp_path / "logger-two.yml"
    log_path_one = tmp_path / "logs" / "one.log"
    log_path_two = tmp_path / "logs" / "two.log"
    level_name = _unique_level_name("name-conflict")
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path_one,
        {
            "levels": {level_name: {"code": _unique_level_code()}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path_one)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )
    _write_yaml(
        config_path_two,
        {
            "levels": {level_name: {"code": _unique_level_code()}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path_two)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    TunnedLogger.from_yaml(config_path_one, name=logger_name, defaults_path=defaults_path, force=True)

    with pytest.raises(ValueError, match="different definition"):
        TunnedLogger.from_yaml(config_path_two, name=logger_name, defaults_path=defaults_path, force=True)


def test_custom_level_conflict_by_code_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path_one = tmp_path / "logger-one.yml"
    config_path_two = tmp_path / "logger-two.yml"
    log_path_one = tmp_path / "logs" / "one.log"
    log_path_two = tmp_path / "logs" / "two.log"
    level_code = _unique_level_code()
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path_one,
        {
            "levels": {_unique_level_name("code-conflict-one"): {"code": level_code}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path_one)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )
    _write_yaml(
        config_path_two,
        {
            "levels": {_unique_level_name("code-conflict-two"): {"code": level_code}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path_two)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    TunnedLogger.from_yaml(config_path_one, name=logger_name, defaults_path=defaults_path, force=True)

    with pytest.raises(ValueError, match="already registered"):
        TunnedLogger.from_yaml(config_path_two, name=logger_name, defaults_path=defaults_path, force=True)


@pytest.mark.parametrize("alias, canonical", [("WARN", "WARNING"), ("FATAL", "CRITICAL")])
def test_level_aliases_are_rejected(
    tmp_path: Path,
    logger_name: str,
    alias: str,
    canonical: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "levels": {alias: {"code": 30}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    with pytest.raises(ValueError, match=f"Use {canonical} instead of {alias}"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_input_level_is_rejected_in_favor_of_prompt(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "levels": {"INPUT": {"code": 15}},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    with pytest.raises(ValueError, match="top-level prompt"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_show_icon_on_non_custom_rich_handler_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {
                "stream": {
                    "class": "logging.StreamHandler",
                    "show_icon": True,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["stream"]},
        },
    )

    with pytest.raises(ValueError, match="not a TunnedHandler"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_show_icon_must_be_boolean(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {
                "console": {
                    "()": "tunning.TunnedHandler",
                    "show_icon": "yes",
                }
            },
            "root": {"level": "DEBUG", "handlers": ["console"]},
        },
    )

    with pytest.raises(ValueError, match="show_icon must be a boolean"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_invalid_human_readable_max_bytes_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(log_path),
                    "maxBytes": "not a size",
                }
            },
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    with pytest.raises(ValueError, match="Invalid maxBytes"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_explicit_requested_logger_config_is_supported(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "loggers": {
                logger_name: {
                    "level": "INFO",
                    "handlers": ["file"],
                    "propagate": False,
                }
            },
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)

    assert logger.level == logging.INFO
    assert logger.propagate is False
    assert log_path.exists()


def test_unexpected_logger_entries_raise(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "loggers": {
                "other.logger": {
                    "level": "INFO",
                    "handlers": ["file"],
                }
            },
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    with pytest.raises(ValueError, match="unexpected entries"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_config_without_root_or_requested_logger_raises(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
        },
    )

    with pytest.raises(ValueError, match="either root or the requested logger"):
        TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)


def test_prompt_uses_symbol_when_icons_are_disabled(
    tmp_path: Path,
    logger_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "logs" / "app.log"
    config_path = tmp_path / "logger.yml"
    _write_yaml(
        config_path,
        {
            "handlers": {
                "console": {"show_icon": False},
                "file": {"filename": str(log_path)},
            }
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, force=True)
    handler = _console_handler(logger)
    captured: dict[str, object] = {}

    def fake_input(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "typed value"

    monkeypatch.setattr(handler.console, "input", fake_input)

    value = logger.prompt("Enter a value")

    assert value == "typed value"
    assert "<<<" in captured["prompt"].plain
    assert "Enter a value" in captured["prompt"].plain


def test_prompt_falls_back_to_new_console_without_custom_rich_handler(
    tmp_path: Path,
    logger_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "app.log"
    captured: dict[str, object] = {}
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "prompt": {"symbol": "??", "icon": "!!", "style": "green"},
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "root": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    def fake_input(self, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "fallback value"

    monkeypatch.setattr(tunning_module.Console, "input", fake_input)
    logger = TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)

    value = logger.prompt("Fallback prompt")

    assert value == "fallback value"
    assert "??" in captured["prompt"].plain
    assert "Fallback prompt" in captured["prompt"].plain
    assert captured["kwargs"]["markup"] is False
    assert captured["kwargs"]["password"] is False


def test_custom_level_with_hyphen_creates_snake_case_method_and_logs(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "custom.log"
    level_name = _unique_level_name("method-level")
    level_code = _unique_level_code()
    method_name = level_name.lower().replace("-", "_")
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "levels": {
                level_name: {
                    "code": level_code,
                    "symbol": "ML",
                    "style": "green",
                }
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_path),
                    "level": level_name,
                }
            },
            "root": {"level": level_name, "handlers": ["file"]},
        },
    )

    logger = TunnedLogger.from_yaml(config_path, name=logger_name, defaults_path=defaults_path, force=True)
    log_method = getattr(logger, method_name)

    log_method("custom method message")
    for handler in logger.handlers:
        handler.flush()

    assert "custom method message" in log_path.read_text(encoding="utf8")
