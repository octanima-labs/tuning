from __future__ import annotations

import logging
import logging.handlers
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import bitmath
import pytest
import yaml
from rich.panel import Panel
from rich.text import Text

import tunning
import tunning.logger as tunning_module
from tunning import TunnedHandler, TunnedLogger


def _write_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf8") as file_handle:
        yaml.safe_dump(data, file_handle, sort_keys=False)


def _write_empty_defaults(path: Path) -> None:
    _write_yaml(path, {})


def _packaged_config_text() -> str:
    return Path(tunning_module.__file__).with_name("conf.yml").read_text(encoding="utf8")


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


def _file_handler(logger: logging.Logger) -> Any:
    for handler in logger.handlers:
        if hasattr(handler, "baseFilename"):
            return handler
    raise AssertionError("Expected a file handler")


def _flush_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.flush()


def _log_record(
    *,
    level: int = logging.INFO,
    message: str = "test output",
    lineno: int = 1,
) -> logging.LogRecord:
    return logging.LogRecord(
        name="tests.console-render",
        level=level,
        pathname=__file__,
        lineno=lineno,
        msg=message,
        args=(),
        exc_info=None,
    )


def _remove_current_root_handlers(root_logger: logging.Logger) -> None:
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


def _has_full_style_span(text: Text, style: str) -> bool:
    return any(
        span.start == 0 and span.end == len(text) and span.style == style for span in text.spans
    )


def _has_content_style_span(text: Text, style: str) -> bool:
    return any(
        span.start == 0 and span.end == len(text) - 1 and span.style == style for span in text.spans
    )


@pytest.fixture
def logger_name() -> Iterator[str]:
    name = f"tests.{uuid.uuid4().hex}"
    yield name
    _drop_logger(name)


@pytest.fixture
def clean_root_logger() -> Iterator[logging.Logger]:
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    original_disabled = root_logger.disabled

    for handler in original_handlers:
        root_logger.removeHandler(handler)

    yield root_logger

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)
    root_logger.disabled = original_disabled


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
    assert file_handler.maxBytes == int(bitmath.parse_string("5 MB").bytes)
    assert log_path.parent.exists()
    assert log_path.exists()

    logger.trace("trace message")


def test_get_logger_returns_tunned_logger(logger_name: str) -> None:
    logger = tunning.getLogger(logger_name)

    assert isinstance(logger, TunnedLogger)
    assert tunning.getLogger(logger_name) is logger
    assert hasattr(logger, "trace")
    assert hasattr(logger, "success")


def test_export_is_available_from_top_level_package() -> None:
    assert tunning.export is tunning_module.export


def test_export_writes_packaged_config_to_directory(tmp_path: Path) -> None:
    exported_path = tunning.export(tmp_path)

    assert exported_path == (tmp_path / "tunning.yml").resolve()
    assert exported_path.read_text(encoding="utf8") == _packaged_config_text()


def test_export_writes_explicit_file_path(tmp_path: Path) -> None:
    target_path = tmp_path / "custom.yml"

    exported_path = tunning.export(target_path)

    assert exported_path == target_path.resolve()
    assert target_path.read_text(encoding="utf8") == _packaged_config_text()


def test_export_treats_nonexistent_extensionless_path_as_file(tmp_path: Path) -> None:
    target_path = tmp_path / "config"

    exported_path = tunning.export(target_path)

    assert exported_path == target_path.resolve()
    assert target_path.is_file()
    assert target_path.read_text(encoding="utf8") == _packaged_config_text()


def test_export_raises_when_target_file_exists(tmp_path: Path) -> None:
    target_path = tmp_path / "tunning.yml"
    target_path.write_text("existing config", encoding="utf8")

    with pytest.raises(FileExistsError, match="already exists"):
        tunning.export(target_path)

    assert target_path.read_text(encoding="utf8") == "existing config"


def test_export_force_overwrites_existing_file(tmp_path: Path) -> None:
    target_path = tmp_path / "tunning.yml"
    target_path.write_text("existing config", encoding="utf8")

    exported_path = tunning.export(target_path, force=True)

    assert exported_path == target_path.resolve()
    assert target_path.read_text(encoding="utf8") == _packaged_config_text()


def test_export_creates_parent_directories(tmp_path: Path) -> None:
    target_path = tmp_path / "nested" / "config" / "tunning.yml"

    exported_path = tunning.export(target_path)

    assert exported_path == target_path.resolve()
    assert target_path.read_text(encoding="utf8") == _packaged_config_text()


def test_export_none_writes_to_calling_file_directory(tmp_path: Path) -> None:
    caller_dir = tmp_path / "my-cool-app"
    caller_dir.mkdir()
    script_path = caller_dir / "main.py"
    repo_root = Path(__file__).parents[1]
    script_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(repo_root)!r})\n"
        "import tunning\n"
        "path = tunning.export()\n"
        "print(path)\n",
        encoding="utf8",
    )

    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    exported_path = caller_dir / "tunning.yml"
    assert result.stdout.strip() == str(exported_path.resolve())
    assert exported_path.read_text(encoding="utf8") == _packaged_config_text()


def test_zero_config_installs_console_only_root_handler_on_first_use(
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    logger = tunning.getLogger(logger_name)
    _remove_current_root_handlers(clean_root_logger)

    logger.info("zero config output")

    assert len(clean_root_logger.handlers) == 1
    assert isinstance(clean_root_logger.handlers[0], TunnedHandler)
    assert not any(
        isinstance(handler, logging.FileHandler) for handler in clean_root_logger.handlers
    )
    assert clean_root_logger.level == logging.INFO


def test_zero_config_dynamic_level_methods_log_from_default_metadata(
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    logger = tunning.getLogger(logger_name)
    logger_as_any: Any = logger
    _remove_current_root_handlers(clean_root_logger)

    logger_as_any.success("zero config success")

    assert len(clean_root_logger.handlers) == 1
    assert isinstance(clean_root_logger.handlers[0], TunnedHandler)


def test_zero_config_does_not_replace_existing_root_handlers(
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    _remove_current_root_handlers(clean_root_logger)
    existing_handler = logging.StreamHandler()
    clean_root_logger.addHandler(existing_handler)
    logger = tunning.getLogger(logger_name)

    logger.info("handled elsewhere")

    assert clean_root_logger.handlers == [existing_handler]


def test_zero_config_prompt_uses_default_prompt_style(
    clean_root_logger: logging.Logger,
    logger_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    logger = tunning.getLogger(logger_name)
    _remove_current_root_handlers(clean_root_logger)

    def fake_input(self, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "zero prompt value"

    monkeypatch.setattr(tunning_module.Console, "input", fake_input)

    value = logger.prompt("Zero prompt")

    assert value == "zero prompt value"
    assert len(clean_root_logger.handlers) == 1
    assert isinstance(clean_root_logger.handlers[0], TunnedHandler)
    assert "<<<" in captured["prompt"].plain
    assert "Zero prompt" in captured["prompt"].plain
    assert _has_content_style_span(captured["prompt"], "italic bold black on magenta")


def test_basic_config_configures_root_for_child_loggers(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "myapp.log"
    logger = tunning.getLogger(logger_name)

    tunning.basicConfig(filename=log_path, level="INFO", force=True)

    logger.info("Started")
    logger.debug("Hidden")
    _flush_handlers(clean_root_logger)

    content = log_path.read_text(encoding="utf8")
    assert "Started" in content
    assert "Hidden" not in content
    assert logger.handlers == []
    assert len(clean_root_logger.handlers) == 1


def test_basic_config_is_noop_when_root_already_has_handlers(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "ignored.log"

    tunning.basicConfig(level="INFO", force=True)
    first_handlers = clean_root_logger.handlers[:]
    tunning.basicConfig(filename=log_path, level="ERROR")

    assert clean_root_logger.handlers == first_handlers
    assert isinstance(clean_root_logger.handlers[0], TunnedHandler)
    assert not log_path.exists()


def test_basic_config_applies_console_handler_options(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(
        level="INFO",
        force=True,
        show_icon=True,
        show_path=True,
        show_time=True,
        boxes=True,
        rich_tracebacks=False,
        markup=False,
    )

    handler = _console_handler(clean_root_logger)

    assert handler.show_icon is True
    assert handler._log_render.show_path is True
    assert handler._log_render.show_time is True
    assert handler.boxes is True
    assert handler.rich_tracebacks is False
    assert handler.markup is False


def test_iso_format_is_exported_for_console_timestamps() -> None:
    assert tunning.ISO_FORMAT == "[%Y-%m-%d %H:%M:%S]"


def test_rotation_defaults_are_exported() -> None:
    assert tunning.DEFAULT_MAX_BYTES == int(bitmath.parse_string("10 MB").bytes)
    assert tunning.DEFAULT_BACKUP_COUNT == 3


def test_basic_config_datefmt_controls_console_timestamp(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(
        level="INFO",
        force=True,
        show_time=True,
        datefmt=tunning.ISO_FORMAT,
    )
    handler = _console_handler(clean_root_logger)
    record = _log_record()
    record.created = datetime(2026, 5, 4, 1, 58, 41).timestamp()

    rendered_time = handler._render_log_time(record)

    assert rendered_time.plain == "[2026-05-04 01:58:41] "


def test_yaml_log_time_format_controls_console_timestamp(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
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
                    "level": "INFO",
                    "show_time": True,
                    "log_time_format": tunning.ISO_FORMAT,
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
        },
    )

    tunning.basicConfigFromYaml(
        config_path,
        defaults_path=defaults_path,
        force=True,
    )
    handler = _console_handler(clean_root_logger)
    record = _log_record()
    record.created = datetime(2026, 5, 4, 1, 58, 41).timestamp()

    rendered_time = handler._render_log_time(record)

    assert rendered_time.plain == "[2026-05-04 01:58:41] "


def test_console_handler_applies_level_style_to_message(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="INFO", force=True)
    handler = _console_handler(clean_root_logger)
    record = logging.LogRecord(
        name="tests.console-style",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="styled output",
        args=(),
        exc_info=None,
    )

    message = handler.render_message(record, record.getMessage())

    assert isinstance(message, Text)
    assert message.plain == "styled output"
    assert _has_full_style_span(message, "cyan")


def test_console_handler_uses_compact_symbol_prefix_width(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="INFO", force=True)
    handler = _console_handler(clean_root_logger)
    record = logging.LogRecord(
        name="tests.console-prefix",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="compact output",
        args=(),
        exc_info=None,
    )

    level_text = handler.get_level_text(record)

    assert level_text.plain == "[*]"
    assert level_text.cell_len == 3
    assert _has_full_style_span(level_text, "cyan")


def test_console_handler_styles_level_separator_with_prefix(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="INFO", force=True)
    handler = _console_handler(clean_root_logger)
    record = logging.LogRecord(
        name="tests.console-prefix",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="compact output",
        args=(),
        exc_info=None,
    )

    level_text = handler._render_level_with_separator(record)

    assert level_text.plain == "[*] "
    assert level_text.cell_len == 4
    assert _has_full_style_span(level_text, "cyan")


def test_console_handler_uses_compact_icon_prefix_width(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="INFO", force=True, show_icon=True)
    handler = _console_handler(clean_root_logger)
    record = logging.LogRecord(
        name="tests.console-prefix",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="compact output",
        args=(),
        exc_info=None,
    )

    level_text = handler.get_level_text(record)

    assert level_text.plain.startswith("🔵")
    assert level_text.cell_len == 3
    assert _has_full_style_span(level_text, "cyan")


def test_console_handler_styles_background_level_separator(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="CRITICAL", force=True)
    handler = _console_handler(clean_root_logger)
    record = logging.LogRecord(
        name="tests.console-prefix",
        level=logging.CRITICAL,
        pathname=__file__,
        lineno=1,
        msg="critical output",
        args=(),
        exc_info=None,
    )

    level_text = handler._render_level_with_separator(record)

    assert level_text.plain == "!!! "
    assert _has_full_style_span(level_text, "bold white on red")


def test_console_handler_renders_boxed_record_with_level_title(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="INFO", force=True, boxes=True)
    handler = _console_handler(clean_root_logger)
    record = _log_record(message="boxed output")
    message = handler.render_message(record, record.getMessage())

    rendered = handler.render(
        record=record,
        traceback="traceback output",
        message_renderable=message,
    )

    panel = rendered.columns[0]._cells[0]
    assert isinstance(panel, Panel)
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "[*] INFO"
    assert panel.border_style == "cyan"
    assert panel.style == "cyan"
    assert _has_full_style_span(panel.title, "cyan")
    panel_body: Any = panel.renderable
    assert panel_body._renderables == [message, "traceback output"]


def test_boxed_render_styles_critical_panel_fill(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(level="CRITICAL", force=True, boxes=True)
    handler = _console_handler(clean_root_logger)
    record = _log_record(level=logging.CRITICAL, message="critical boxed output")
    message = handler.render_message(record, record.getMessage())

    rendered = handler.render(record=record, traceback=None, message_renderable=message)

    panel = rendered.columns[0]._cells[0]
    assert isinstance(panel, Panel)
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "!!! CRITICAL"
    assert panel.border_style == "bold white on red"
    assert panel.style == "bold white on red"
    assert _has_full_style_span(panel.title, "bold white on red")


def test_boxed_render_keeps_time_and_path_outside_panel(
    clean_root_logger: logging.Logger,
) -> None:
    tunning.basicConfig(
        level="INFO",
        force=True,
        boxes=True,
        show_time=True,
        show_path=True,
    )
    handler = _console_handler(clean_root_logger)
    record = _log_record(message="boxed output", lineno=123)
    message = handler.render_message(record, record.getMessage())

    rendered = handler.render(record=record, traceback=None, message_renderable=message)

    assert len(rendered.columns) == 3
    assert isinstance(rendered.columns[1]._cells[0], Panel)
    assert rendered.columns[0]._cells[0].plain.endswith(" ")
    assert "test_tunned_logger.py:123" in rendered.columns[2]._cells[0].plain


def test_boxed_render_honors_hidden_level() -> None:
    handler = TunnedHandler(boxes=True, show_level=False, show_time=False)
    record = _log_record(message="untitled boxed output")
    message = handler.render_message(record, record.getMessage())

    rendered = handler.render(record=record, traceback=None, message_renderable=message)

    panel = rendered.columns[0]._cells[0]
    assert isinstance(panel, Panel)
    assert panel.title is None


def test_console_handler_keeps_long_fallback_labels_untruncated() -> None:
    handler = TunnedHandler()
    record = logging.LogRecord(
        name="tests.console-prefix",
        level=123456,
        pathname=__file__,
        lineno=1,
        msg="long label output",
        args=(),
        exc_info=None,
    )
    record.levelname = "MY-LONG-LEVEL"

    level_text = handler.get_level_text(record)

    assert level_text.plain == "[MY-LONG-LEVEL]"
    assert level_text.cell_len > 3
    assert _has_full_style_span(level_text, "logging.level.my-long-level")


def test_basic_config_force_replaces_root_handlers(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "forced.log"
    logger = tunning.getLogger(logger_name)

    tunning.basicConfig(level="INFO")
    tunning.basicConfig(filename=log_path, level="INFO", force=True)

    logger.info("forced output")
    _flush_handlers(clean_root_logger)

    assert len(clean_root_logger.handlers) == 1
    assert "forced output" in log_path.read_text(encoding="utf8")


def test_basic_config_filename_is_file_only_and_uses_detailed_formatter(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "file-only.log"
    logger = tunning.getLogger(logger_name)

    tunning.basicConfig(
        filename=log_path,
        level="INFO",
        force=True,
        show_icon=True,
        show_path=True,
        show_time=True,
        rich_tracebacks=False,
        markup=False,
    )

    logger.info("file-only output")
    _flush_handlers(clean_root_logger)

    assert len(clean_root_logger.handlers) == 1
    assert not isinstance(clean_root_logger.handlers[0], TunnedHandler)
    assert clean_root_logger.handlers[0].formatter is not None
    assert (
        clean_root_logger.handlers[0].formatter._fmt
        == "%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"
    )
    content = log_path.read_text(encoding="utf8")
    assert "[INFO]" in content
    assert logger_name in content
    assert "test_basic_config_filename_is_file_only_and_uses_detailed_formatter" in content
    assert "file-only output" in content


def test_basic_config_filename_with_console_creates_file_and_console_handlers(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "with-console.log"
    logger = tunning.getLogger(logger_name)

    tunning.basicConfig(
        filename=log_path,
        console=True,
        level="INFO",
        force=True,
        show_icon=True,
    )

    logger.info("console and file output")
    _flush_handlers(clean_root_logger)

    assert len(clean_root_logger.handlers) == 2
    assert isinstance(clean_root_logger.handlers[0], logging.FileHandler)
    assert _console_handler(clean_root_logger).show_icon is True
    assert "console and file output" in log_path.read_text(encoding="utf8")


def test_basic_config_filename_without_rotation_uses_plain_file_handler(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "plain.log"

    tunning.basicConfig(filename=log_path, level="INFO", force=True)

    file_handler = clean_root_logger.handlers[0]
    assert isinstance(file_handler, logging.FileHandler)
    assert not isinstance(file_handler, logging.handlers.RotatingFileHandler)


def test_basic_config_max_bytes_uses_rotating_file_handler(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "rotating.log"

    tunning.basicConfig(
        filename=log_path,
        level="INFO",
        force=True,
        max_bytes=1024,
        backup_count=5,
    )

    file_handler = clean_root_logger.handlers[0]
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.maxBytes == 1024
    assert file_handler.backupCount == 5
    assert file_handler.formatter is not None
    assert (
        file_handler.formatter._fmt
        == "%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"
    )


def test_basic_config_accepts_human_readable_max_bytes(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "human-readable.log"

    tunning.basicConfig(
        filename=log_path,
        level="INFO",
        force=True,
        max_bytes="2 MB",
        backup_count=2,
    )

    file_handler = clean_root_logger.handlers[0]
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.maxBytes == int(bitmath.parse_string("2 MB").bytes)
    assert file_handler.backupCount == 2


def test_basic_config_max_bytes_without_backup_count_warns_and_uses_default(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "default-backups.log"

    with pytest.warns(UserWarning, match="DEFAULT_BACKUP_COUNT"):
        tunning.basicConfig(
            filename=log_path,
            level="INFO",
            force=True,
            max_bytes="1 MB",
        )

    file_handler = clean_root_logger.handlers[0]
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.maxBytes == int(bitmath.parse_string("1 MB").bytes)
    assert file_handler.backupCount == tunning.DEFAULT_BACKUP_COUNT


def test_basic_config_backup_count_without_max_bytes_warns_and_uses_default(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
) -> None:
    log_path = tmp_path / "logs" / "default-max-bytes.log"

    with pytest.warns(UserWarning, match="DEFAULT_MAX_BYTES"):
        tunning.basicConfig(
            filename=log_path,
            level="INFO",
            force=True,
            backup_count=4,
        )

    file_handler = clean_root_logger.handlers[0]
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.maxBytes == tunning.DEFAULT_MAX_BYTES
    assert file_handler.backupCount == 4


def test_basic_config_ignores_rotation_options_without_filename(
    clean_root_logger: logging.Logger,
) -> None:
    kwargs: dict[str, Any] = {
        "level": "INFO",
        "force": True,
        "max_bytes": object(),
        "backup_count": -1,
    }

    tunning.basicConfig(**kwargs)

    assert len(clean_root_logger.handlers) == 1
    assert isinstance(clean_root_logger.handlers[0], TunnedHandler)


@pytest.mark.parametrize("max_bytes", [0, -1, True, object(), "not a size"])
def test_basic_config_invalid_max_bytes_raises(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    max_bytes: Any,
) -> None:
    log_path = tmp_path / "logs" / "invalid-size.log"

    with pytest.raises(ValueError, match="max_bytes"):
        tunning.basicConfig(
            filename=log_path,
            level="INFO",
            force=True,
            max_bytes=max_bytes,
            backup_count=1,
        )


@pytest.mark.parametrize("backup_count", [-1, True, object(), "3"])
def test_basic_config_invalid_backup_count_raises(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    backup_count: Any,
) -> None:
    log_path = tmp_path / "logs" / "invalid-backups.log"

    with pytest.raises(ValueError, match="backup_count"):
        tunning.basicConfig(
            filename=log_path,
            level="INFO",
            force=True,
            max_bytes=1024,
            backup_count=backup_count,
        )


@pytest.mark.parametrize(
    "option",
    ["console", "show_icon", "show_path", "show_time", "rich_tracebacks", "markup"],
)
def test_basic_config_boolean_options_must_be_boolean(
    clean_root_logger: logging.Logger,
    option: str,
) -> None:
    kwargs: dict[str, Any] = {option: "yes"}

    with pytest.raises(ValueError, match=f"{option} must be a boolean"):
        tunning.basicConfig(force=True, **kwargs)


def test_basic_config_installs_default_custom_level_methods(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    log_path = tmp_path / "logs" / "trace.log"
    logger = tunning.getLogger(logger_name)

    tunning.basicConfig(filename=log_path, level="TRACE", force=True)

    logger_as_any: Any = logger
    logger_as_any.trace("trace output")
    _flush_handlers(clean_root_logger)

    assert "trace output" in log_path.read_text(encoding="utf8")


def test_basic_config_from_yaml_configures_actual_root_logger(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "root.log"
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "handlers": {"file": {"class": "logging.FileHandler", "filename": str(log_path)}},
            "root": {"level": "INFO", "handlers": ["file"]},
        },
    )
    logger = tunning.getLogger(logger_name)

    tunning.basicConfigFromYaml(config_path, defaults_path=defaults_path, force=True)

    logger.info("root inherited output")
    _flush_handlers(clean_root_logger)

    assert logger.handlers == []
    assert len(clean_root_logger.handlers) == 1
    assert "root inherited output" in log_path.read_text(encoding="utf8")


def test_basic_config_from_yaml_without_path_loads_packaged_defaults(
    clean_root_logger: logging.Logger,
    logger_name: str,
) -> None:
    logger = tunning.getLogger(logger_name)

    tunning.basicConfigFromYaml(force=True)

    logger.info("packaged default output")
    _flush_handlers(clean_root_logger)

    assert any(isinstance(handler, TunnedHandler) for handler in clean_root_logger.handlers)
    assert any(isinstance(handler, logging.FileHandler) for handler in clean_root_logger.handlers)


def test_basic_config_from_yaml_prompt_uses_inherited_root_handler(
    tmp_path: Path,
    clean_root_logger: logging.Logger,
    logger_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    captured: dict[str, Any] = {}
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "prompt": {"symbol": "??", "icon": "!!", "style": "green"},
            "handlers": {
                "console": {
                    "()": "tunning.TunnedHandler",
                    "level": "DEBUG",
                    "show_icon": True,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["console"]},
        },
    )
    logger = tunning.getLogger(logger_name)

    tunning.basicConfigFromYaml(config_path, defaults_path=defaults_path, force=True)
    handler = _console_handler(clean_root_logger)

    def fake_input(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "typed root value"

    monkeypatch.setattr(handler.console, "input", fake_input)

    value = logger.prompt("Root prompt")

    assert value == "typed root value"
    assert "!!" in captured["prompt"].plain
    assert "Root prompt" in captured["prompt"].plain
    assert captured["prompt"].plain.endswith(" ")
    assert _has_content_style_span(captured["prompt"], "green")
    assert not _has_full_style_span(captured["prompt"], "green")


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
    captured: dict[str, Any] = {}

    def fake_input(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "typed value"

    monkeypatch.setattr(handler.console, "input", fake_input)

    value = logger.prompt("Enter a value")

    assert value == "typed value"
    assert "📝" in captured["prompt"].plain
    assert "Enter a value" in captured["prompt"].plain
    assert captured["prompt"].plain.endswith(" ")
    assert _has_content_style_span(captured["prompt"], "italic bold black on magenta")
    assert not _has_full_style_span(captured["prompt"], "italic bold black on magenta")
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
    assert Path(_file_handler(reconfigured_logger).baseFilename) == log_path_two.resolve()


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
    assert console_handler.boxes is False
    assert console_handler.markup is True
    assert file_handler.maxBytes == int(bitmath.parse_string("5 MB").bytes)
    assert file_handler.backupCount == 3


def test_boxes_from_yaml_configures_tunned_handler(
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
                    "boxes": True,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["console"]},
        },
    )

    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )

    assert _console_handler(logger).boxes is True


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

    TunnedLogger.from_yaml(
        config_path_one, name=logger_name, defaults_path=defaults_path, force=True
    )

    with pytest.raises(ValueError, match="different definition"):
        TunnedLogger.from_yaml(
            config_path_two, name=logger_name, defaults_path=defaults_path, force=True
        )


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

    TunnedLogger.from_yaml(
        config_path_one, name=logger_name, defaults_path=defaults_path, force=True
    )

    with pytest.raises(ValueError, match="already registered"):
        TunnedLogger.from_yaml(
            config_path_two, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


def test_boxes_on_non_custom_rich_handler_raises(
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
                    "boxes": True,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["stream"]},
        },
    )

    with pytest.raises(ValueError, match="not a TunnedHandler"):
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


def test_boxes_must_be_boolean(
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
                    "boxes": "yes",
                }
            },
            "root": {"level": "DEBUG", "handlers": ["console"]},
        },
    )

    with pytest.raises(ValueError, match="boxes must be a boolean"):
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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

    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )

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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
        TunnedLogger.from_yaml(
            config_path, name=logger_name, defaults_path=defaults_path, force=True
        )


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
    captured: dict[str, Any] = {}

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
    captured: dict[str, Any] = {}
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
    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )

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

    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )
    log_method = getattr(logger, method_name)

    log_method("custom method message")
    for handler in logger.handlers:
        handler.flush()

    assert "custom method message" in log_path.read_text(encoding="utf8")


def test_custom_level_reports_user_call_site(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "caller.log"
    level_name = _unique_level_name("caller-level")
    level_code = _unique_level_code()
    method_name = level_name.lower().replace("-", "_")
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "levels": {level_name: {"code": level_code, "symbol": "CL"}},
            "formatters": {"caller": {"format": "%(filename)s:%(funcName)s:%(message)s"}},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_path),
                    "formatter": "caller",
                    "level": level_name,
                }
            },
            "root": {"level": level_name, "handlers": ["file"]},
        },
    )

    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )
    log_method = getattr(logger, method_name)

    log_method("custom caller message")
    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf8")
    assert "test_tunned_logger.py:test_custom_level_reports_user_call_site" in content
    assert "_levels.py" not in content


def test_custom_level_respects_user_stacklevel(
    tmp_path: Path,
    logger_name: str,
) -> None:
    defaults_path = tmp_path / "defaults.yml"
    config_path = tmp_path / "logger.yml"
    log_path = tmp_path / "logs" / "stacklevel.log"
    level_name = _unique_level_name("stacklevel")
    level_code = _unique_level_code()
    method_name = level_name.lower().replace("-", "_")
    _write_empty_defaults(defaults_path)
    _write_yaml(
        config_path,
        {
            "levels": {level_name: {"code": level_code, "symbol": "SL"}},
            "formatters": {"caller": {"format": "%(filename)s:%(funcName)s:%(message)s"}},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_path),
                    "formatter": "caller",
                    "level": level_name,
                }
            },
            "root": {"level": level_name, "handlers": ["file"]},
        },
    )

    logger = TunnedLogger.from_yaml(
        config_path, name=logger_name, defaults_path=defaults_path, force=True
    )
    log_method = getattr(logger, method_name)

    def helper() -> None:
        log_method("custom stacklevel message", stacklevel=2)

    helper()
    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf8")
    assert "test_tunned_logger.py:test_custom_level_respects_user_stacklevel" in content
    assert "helper" not in content
    assert "_levels.py" not in content
