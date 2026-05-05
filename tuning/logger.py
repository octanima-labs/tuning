"""Public logging APIs for tuning."""

from __future__ import annotations

import logging
import logging.config
import logging.handlers
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, overload

from rich.cells import cell_len
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

from tuning._config import (
    export_default_config,
    load_tuning_config,
    load_tuning_metadata,
    load_tuning_root_config,
    parse_size_to_bytes,
)
from tuning._levels import (
    get_level_spec,
    install_dynamic_level_methods,
    parse_runtime_level_spec,
    register_level_specs,
    validate_dynamic_level_methods,
    validate_level_specs,
)
from tuning._models import LevelSpec, PromptSpec
from tuning._prompt import render_prompt_text

ISO_FORMAT = "[%Y-%m-%d %H:%M:%S]"
"""ISO-like console timestamp format for `basicConfig(datefmt=...)`."""

DEFAULT_MAX_BYTES = parse_size_to_bytes("10 MB", field_name="DEFAULT_MAX_BYTES")
"""Default rotating file size used when only `backup_count` is provided."""

DEFAULT_BACKUP_COUNT = 3
"""Default number of rotated log files kept when only `max_bytes` is provided."""
_DETAILED_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"
_LEVEL_PREFIX_MIN_WIDTH = 3
_ZERO_CONFIG_LEVEL = "INFO"
_ROOT_PROMPT_SPEC = PromptSpec()
_DEFAULT_METADATA_INSTALLED = False
_ZERO_CONFIGURING = False


class TunedHandler(RichHandler):
    """Rich console handler that renders tuning level metadata.

    `TunedHandler` extends Rich's `RichHandler` with symbol/icon level
    prefixes, full-message level styling, and optional per-record boxes.
    It is normally created through `basicConfig()` or YAML configuration rather
    than instantiated directly.
    """

    def __init__(
        self,
        *args: Any,
        show_icon: bool = False,
        boxes: bool = False,
        **kwargs: Any,
    ) -> None:
        """Create a console handler.

        Args:
            *args: Positional arguments passed to `rich.logging.RichHandler`.
            show_icon: Use configured level icons instead of symbols when an
                icon is available.
            boxes: Render each console log record inside a Rich panel.
            **kwargs: Keyword arguments passed to `rich.logging.RichHandler`.
        """
        super().__init__(*args, **kwargs)
        self.show_icon = show_icon
        self.boxes = boxes

    def get_level_text(self, record: logging.LogRecord) -> Text:
        prefix = self._get_level_prefix(record)
        rendered_prefix = _pad_level_prefix(prefix)
        return Text.styled(rendered_prefix, _level_prefix_style(record))

    def _get_level_prefix(self, record: logging.LogRecord) -> str:
        spec = get_level_spec(record.levelname)
        if spec is None:
            return f"[{record.levelname}]"

        if self.show_icon and spec.icon:
            return spec.icon
        if spec.symbol:
            return spec.symbol
        return f"[{record.levelname}]"

    def render_message(self, record: logging.LogRecord, message: str) -> Any:
        message_renderable = super().render_message(record, message)
        style = _level_style(record)
        if style and isinstance(message_renderable, Text):
            message_renderable.stylize(style, 0, len(message_renderable))

        return message_renderable

    def render(
        self,
        *,
        record: logging.LogRecord,
        traceback: Any,
        message_renderable: Any,
    ) -> Any:
        from rich.containers import Renderables
        from rich.panel import Panel
        from rich.table import Table

        log_render = self._log_render
        output = Table.grid(padding=(0, 0))
        output.expand = True
        if log_render.show_time:
            output.add_column(style="log.time")
        if log_render.show_level and not self.boxes:
            output.add_column(style="log.level", width=log_render.level_width)
        output.add_column(ratio=1, style="log.message", overflow="fold")
        path = Path(record.pathname).name
        if log_render.show_path and path:
            output.add_column(style="log.path")

        row: list[Any] = []
        if log_render.show_time:
            row.append(self._render_log_time(record))
        if log_render.show_level and not self.boxes:
            row.append(self._render_level_with_separator(record))

        body = Renderables(
            [message_renderable] if not traceback else [message_renderable, traceback]
        )
        if self.boxes:
            row.append(
                Panel(
                    body,
                    title=self._render_box_title(record) if log_render.show_level else None,
                    title_align="left",
                    border_style=_level_prefix_style(record),
                    style=_level_prefix_style(record),
                    expand=True,
                )
            )
        else:
            row.append(body)

        if log_render.show_path and path:
            row.append(self._render_log_path(record, path))

        output.add_row(*row)
        return output

    def _render_box_title(self, record: logging.LogRecord) -> Text:
        title = Text(f"{self._get_level_prefix(record)} {record.levelname}")
        title.stylize(_level_prefix_style(record), 0, len(title))
        return title

    def _render_level_with_separator(self, record: logging.LogRecord) -> Text:
        level_text = self.get_level_text(record).copy()
        level_text.append(" ")
        level_text.stylize(_level_prefix_style(record), 0, len(level_text))
        return level_text

    def _render_log_time(self, record: logging.LogRecord) -> Text:
        log_render = self._log_render
        log_time = datetime.fromtimestamp(record.created)
        time_format: Any = self.formatter.datefmt if self.formatter is not None else None
        time_format = time_format or log_render.time_format

        if callable(time_format):
            log_time_display = time_format(log_time)
        else:
            log_time_display = Text(log_time.strftime(time_format))

        if log_time_display == log_render._last_time and log_render.omit_repeated_times:
            rendered_time = Text(" " * len(log_time_display))
        else:
            log_render._last_time = log_time_display
            rendered_time = log_time_display.copy()

        rendered_time.append(" ")
        return rendered_time

    def _render_log_path(self, record: logging.LogRecord, path: str) -> Text:
        link_path = record.pathname if self.enable_link_path else None
        path_text = Text(" ")
        path_text.append(path, style=f"link file://{link_path}" if link_path else "")
        if record.lineno:
            path_text.append(":")
            path_text.append(
                f"{record.lineno}",
                style=f"link file://{link_path}#{record.lineno}" if link_path else "",
            )
        return path_text


class TunedLogger(logging.Logger):
    """Logger subclass with YAML configuration and styled prompts.

    `TunedLogger` behaves like a normal stdlib logger while adding
    `from_yaml()` for named logger configuration and `prompt()` for styled
    interactive input.
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self._tuning_signature: str | None = None
        self._prompt_spec: PromptSpec | None = None

    def isEnabledFor(self, level: int) -> bool:
        _ensure_zero_configured()
        return super().isEnabledFor(level)

    @classmethod
    def from_yaml(
        cls,
        config_path: str | Path,
        *,
        name: str = "app",
        defaults_path: str | Path | None = None,
        force: bool = False,
    ) -> TunedLogger:
        """Configure and return one named `TunedLogger` from YAML.

        The packaged `tuning/conf.yml` defaults are loaded first, then
        `config_path` is deep-merged on top. This method configures only the
        requested named logger. If the YAML defines only `root`, that section is
        used as the template for the named logger and does not configure the
        process root logger.

        Args:
            config_path: YAML override path.
            name: Logger name to configure.
            defaults_path: Optional defaults file used instead of the packaged
                config. Intended for tests and advanced integrations.
            force: Replace existing managed handlers for the same logger.

        Returns:
            The configured `TunedLogger`.

        Raises:
            ValueError: If the logger name is invalid, the logger already exists
                as a non-`TunedLogger`, or an existing configuration would be
                replaced without `force=True`.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Logger name must be a non-empty string")

        resolved_config = load_tuning_config(
            config_path,
            logger_name=name,
            defaults_path=defaults_path,
        )
        logger = _get_or_create_tuned_logger(name)

        existing_signature = logger._tuning_signature
        if existing_signature == resolved_config.signature and not force:
            return logger

        if existing_signature and existing_signature != resolved_config.signature and not force:
            raise ValueError(
                f"TunedLogger {name!r} is already configured with a different config; use force=True"
            )

        if existing_signature is None and logger.handlers and not force:
            raise ValueError(
                f"TunedLogger {name!r} already has handlers but is not managed by from_yaml; use force=True"
            )

        register_level_specs(resolved_config.level_specs)
        install_dynamic_level_methods(cls, resolved_config.level_specs)

        if force:
            _close_logger_handlers(logger)

        logging.config.dictConfig(resolved_config.logging_config)
        configured_logger = logging.getLogger(name)
        if not isinstance(configured_logger, TunedLogger):
            raise ValueError(f"Configured logger {name!r} is not a TunedLogger")

        configured_logger._tuning_signature = resolved_config.signature
        configured_logger._prompt_spec = resolved_config.prompt_spec
        return configured_logger

    def prompt(
        self,
        message: str,
        *,
        password: bool = False,
        markup: bool | None = None,
    ) -> str:
        """Prompt for interactive input using configured prompt styling.

        Args:
            message: Prompt question to display.
            password: Hide input while typing.
            markup: Whether Rich markup in the prompt message is enabled. If
                omitted, the first inherited `TunedHandler` setting is used.

        Returns:
            The user's typed input.

        Raises:
            ValueError: If `message` is not a string.
            EOFError: If input cannot be read from the console.
        """
        if not isinstance(message, str):
            raise ValueError("Prompt message must be a string")

        _ensure_zero_configured()

        handler = _first_color_handler(self)
        console = handler.console if handler else Console()
        show_icon = handler.show_icon if handler else False
        use_markup = handler.markup if handler and markup is None else bool(markup)

        prompt_text = render_prompt_text(
            self._prompt_spec or _ROOT_PROMPT_SPEC,
            message,
            show_icon=show_icon,
            markup=use_markup,
        )
        return console.input(prompt_text, markup=False, password=password)


@overload
def getLogger(name: str) -> TunedLogger: ...


@overload
def getLogger(name: None = None) -> logging.Logger: ...


def getLogger(name: str | None = None) -> logging.Logger:
    """Return a logger using tuning's logger class for named loggers.

    Args:
        name: Logger name. If omitted, returns the process root logger.

    Returns:
        A `TunedLogger` for named loggers, or the stdlib root logger when
        `name` is omitted.

    Raises:
        ValueError: If `name` is empty or an existing logger with that name is
            not a `TunedLogger`.
    """
    _install_default_metadata()

    if name is None:
        return logging.getLogger()

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Logger name must be a non-empty string")

    return _get_or_create_tuned_logger(name)


def export(path: str | Path | None = None, *, force: bool = False) -> Path:
    """Export the packaged default configuration to a YAML file.

    The exported file is copied from packaged `tuning/conf.yml`; it does not
    reconstruct the current runtime logging state.

    Args:
        path: Destination file path or existing directory. If omitted, writes
            `tuning.yml` next to the calling Python file.
        force: Overwrite an existing target file.

    Returns:
        The resolved path that was written.

    Raises:
        FileExistsError: If the target file exists and `force` is false.
        ValueError: If `force` is not a boolean.
    """
    _validate_bool("force", force)
    return export_default_config(_resolve_export_path(path), force=force)


def addLevel(
    num: int,
    name: str,
    symbol: str | None = None,
    icon: str | None = None,
    style: str | None = None,
) -> None:
    """Register a runtime-only custom log level and logger method.

    The level is added to stdlib logging for the current Python process and a
    matching method is installed on `TunedLogger`. For example,
    `addLevel(7, "MY_CUSTOM_LEVEL")` creates `logger.my_custom_level(...)` for
    existing and future tuning loggers. This does not update YAML files or
    exported configuration.

    Args:
        num: Numeric logging level code.
        name: Custom level name. Names are normalized to uppercase and must
            create a valid Python method name when lowercased.
        symbol: Compact console prefix used when icons are disabled.
        icon: Console prefix used when `show_icon=True`.
        style: Rich style applied to console level prefixes and messages.

    Raises:
        ValueError: If the level definition is invalid or conflicts with an
            existing logging level or dynamic method.
    """
    spec = parse_runtime_level_spec(
        num=num,
        name=name,
        symbol=symbol,
        icon=icon,
        style=style,
    )
    _install_default_metadata()
    validate_level_specs([spec])
    validate_dynamic_level_methods(TunedLogger, [spec])
    register_level_specs([spec])
    install_dynamic_level_methods(TunedLogger, [spec])


def _resolve_export_path(path: str | Path | None) -> Path:
    if path is None:
        return _caller_directory() / "tuning.yml"

    target_path = Path(path).expanduser()
    if target_path.is_dir():
        return target_path / "tuning.yml"

    return target_path


def _caller_directory() -> Path:
    try:
        caller_frame = sys._getframe(3)
    except ValueError:
        return Path.cwd()

    caller_file = caller_frame.f_globals.get("__file__")
    if not isinstance(caller_file, str):
        return Path.cwd()

    return Path(caller_file).resolve().parent


def basicConfig(
    *,
    filename: str | Path | None = None,
    filemode: str = "a",
    max_bytes: int | str | None = None,
    backup_count: int | None = None,
    format: str | None = None,
    datefmt: str | None = None,
    style: str = "%",
    level: int | str | None = logging.WARNING,
    stream: Any | None = None,
    handlers: list[logging.Handler] | None = None,
    force: bool = False,
    encoding: str | None = None,
    errors: str | None = None,
    console: bool = False,
    show_icon: bool = False,
    show_level: bool = True,
    show_path: bool = False,
    show_time: bool = False,
    boxes: bool = False,
    rich_tracebacks: bool = True,
    markup: bool = True,
    defaults_path: str | Path | None = None,
) -> None:
    """Configure the process root logger with tuning defaults.

    This follows stdlib `logging.basicConfig()` semantics: if the root logger
    already has handlers, the call is ignored unless `force=True` is passed.
    Without `filename`, a console `TunedHandler` is installed. With `filename`,
    a detailed file handler is installed; pass `console=True` to install both.

    Args:
        filename: File path for file logging. If omitted, console logging is
            configured instead.
        filemode: File open mode for file handlers.
        max_bytes: Rotation threshold in bytes or as a human-readable size
            string such as `"10 MB"`. Ignored when `filename` is omitted.
        backup_count: Number of rotated log files to keep. Ignored when
            `filename` is omitted.
        format: Formatter format string passed to `logging.basicConfig()`.
        datefmt: Formatter date format. For console timestamps, use this with
            `show_time=True`; `ISO_FORMAT` is provided as a convenience.
        style: Formatter style passed to `logging.basicConfig()`.
        level: Root logger level.
        stream: Console stream target.
        handlers: Explicit handlers. Cannot be combined with `stream`,
            `filename`, or `console`.
        force: Replace existing root handlers.
        encoding: File encoding for file handlers.
        errors: File encoding error handling for file handlers.
        console: Also create a console handler when `filename` is provided.
        show_icon: Use configured level icons instead of symbols.
        show_level: Show level prefixes or boxed level titles in console output.
        show_path: Show source file path in console output.
        show_time: Show timestamps in console output.
        boxes: Render each console log record inside a Rich panel.
        rich_tracebacks: Render Rich tracebacks in console output.
        markup: Enable Rich markup in console messages.
        defaults_path: Optional defaults file used instead of the packaged
            config. Intended for tests and advanced integrations.

    Raises:
        ValueError: If boolean options or rotation values are invalid, or if
            mutually exclusive handler options are combined.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers and not force:
        return

    _validate_bool("console", console)
    _validate_bool("show_icon", show_icon)
    _validate_bool("show_level", show_level)
    _validate_bool("show_path", show_path)
    _validate_bool("show_time", show_time)
    _validate_bool("boxes", boxes)
    _validate_bool("rich_tracebacks", rich_tracebacks)
    _validate_bool("markup", markup)

    if handlers is not None and (filename is not None or stream is not None or console):
        raise ValueError(
            "'stream', 'filename', or 'console' should not be specified together with 'handlers'"
        )
    if filename is not None and stream is not None and not console:
        raise ValueError("'stream' and 'filename' should not be specified together")

    metadata = load_tuning_metadata(defaults_path=defaults_path)
    _install_tuning_metadata(metadata.level_specs, metadata.prompt_spec)

    logging_handlers = handlers
    if logging_handlers is None:
        logging_handlers = []
        if filename is not None:
            logging_handlers.append(
                _make_file_handler(
                    filename,
                    filemode=filemode,
                    max_bytes=max_bytes,
                    backup_count=backup_count,
                    encoding=encoding,
                    errors=errors,
                )
            )

        if filename is None or console:
            logging_handlers.append(
                _make_console_handler(
                    stream=stream,
                    show_icon=show_icon,
                    show_level=show_level,
                    show_path=show_path,
                    show_time=show_time,
                    boxes=boxes,
                    rich_tracebacks=rich_tracebacks,
                    markup=markup,
                )
            )

    basic_config_kwargs: dict[str, Any] = {
        "format": format,
        "datefmt": datefmt,
        "style": style,
        "level": level,
        "handlers": logging_handlers,
        "force": force,
    }
    logging.basicConfig(**basic_config_kwargs)


def _make_console_handler(
    *,
    stream: Any | None,
    show_icon: bool,
    show_level: bool,
    show_path: bool,
    show_time: bool,
    boxes: bool,
    rich_tracebacks: bool,
    markup: bool,
) -> TunedHandler:
    handler_kwargs: dict[str, Any] = {
        "show_icon": show_icon,
        "show_level": show_level,
        "show_path": show_path,
        "show_time": show_time,
        "boxes": boxes,
        "rich_tracebacks": rich_tracebacks,
        "markup": markup,
    }
    if stream is not None:
        handler_kwargs["console"] = Console(file=stream)

    return TunedHandler(**handler_kwargs)


def _make_file_handler(
    filename: str | Path,
    *,
    filemode: str,
    max_bytes: int | str | None,
    backup_count: int | None,
    encoding: str | None,
    errors: str | None,
) -> logging.FileHandler | logging.handlers.RotatingFileHandler:
    log_path = Path(filename).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if max_bytes is None and backup_count is None:
        handler: logging.FileHandler | logging.handlers.RotatingFileHandler = logging.FileHandler(
            log_path,
            mode=filemode,
            encoding=encoding,
            errors=errors,
        )
    else:
        resolved_max_bytes = _resolve_max_bytes(max_bytes)
        resolved_backup_count = _resolve_backup_count(backup_count)
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            mode=filemode,
            maxBytes=resolved_max_bytes,
            backupCount=resolved_backup_count,
            encoding=encoding,
            errors=errors,
        )
    handler.setFormatter(logging.Formatter(_DETAILED_FILE_FORMAT))
    return handler


def _resolve_max_bytes(max_bytes: int | str | None) -> int:
    if max_bytes is None:
        warnings.warn(
            "Rotation enabled, but no max_bytes specified. Using tuning.DEFAULT_MAX_BYTES.",
            stacklevel=4,
        )
        return DEFAULT_MAX_BYTES

    if isinstance(max_bytes, bool):
        raise ValueError("max_bytes must be a positive integer or size string")
    if isinstance(max_bytes, int):
        resolved_max_bytes = max_bytes
    elif isinstance(max_bytes, str):
        resolved_max_bytes = parse_size_to_bytes(max_bytes, field_name="max_bytes")
    else:
        raise ValueError("max_bytes must be a positive integer or size string")

    if resolved_max_bytes <= 0:
        raise ValueError("max_bytes must be greater than 0")

    return resolved_max_bytes


def _resolve_backup_count(backup_count: int | None) -> int:
    if backup_count is None:
        warnings.warn(
            "Rotation enabled, but no backup_count specified. Using tuning.DEFAULT_BACKUP_COUNT.",
            stacklevel=4,
        )
        return DEFAULT_BACKUP_COUNT

    if isinstance(backup_count, bool) or not isinstance(backup_count, int):
        raise ValueError("backup_count must be a non-negative integer")
    if backup_count < 0:
        raise ValueError("backup_count must be greater than or equal to 0")

    return backup_count


def _validate_bool(field_name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")


def _level_style(record: logging.LogRecord) -> str | None:
    spec = get_level_spec(record.levelname)
    if spec is None:
        return None

    return spec.style


def _level_prefix_style(record: logging.LogRecord) -> str:
    spec = get_level_spec(record.levelname)
    if spec is not None and spec.style:
        return spec.style

    return f"logging.level.{record.levelname.lower()}"


def _pad_level_prefix(prefix: str) -> str:
    prefix_width = cell_len(prefix)
    if prefix_width >= _LEVEL_PREFIX_MIN_WIDTH:
        return prefix

    return prefix + " " * (_LEVEL_PREFIX_MIN_WIDTH - prefix_width)


def basicConfigFromYaml(
    config_path: str | Path | None = None,
    *,
    defaults_path: str | Path | None = None,
    force: bool = False,
) -> None:
    """Configure the process root logger from YAML.

    The packaged `tuning/conf.yml` defaults are loaded first. If `config_path`
    is provided, it is deep-merged on top. The resulting config is applied to
    the real process root logger with stdlib `logging.config.dictConfig()`.

    Args:
        config_path: Optional YAML override path. If omitted, packaged defaults
            are used directly.
        defaults_path: Optional defaults file used instead of the packaged
            config. Intended for tests and advanced integrations.
        force: Replace existing root handlers.

    Raises:
        ValueError: If the resolved YAML config is invalid.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers and not force:
        return

    resolved_config = load_tuning_root_config(
        config_path,
        defaults_path=defaults_path,
    )
    _install_tuning_metadata(resolved_config.level_specs, resolved_config.prompt_spec)
    _prepare_configured_tuned_loggers(resolved_config.logging_config)

    if force:
        _close_logger_handlers(root_logger)

    logging.config.dictConfig(resolved_config.logging_config)


def _install_default_metadata() -> None:
    global _DEFAULT_METADATA_INSTALLED

    if _DEFAULT_METADATA_INSTALLED:
        return

    metadata = load_tuning_metadata()
    _install_tuning_metadata(metadata.level_specs, metadata.prompt_spec)
    _DEFAULT_METADATA_INSTALLED = True


def _ensure_zero_configured() -> None:
    global _ZERO_CONFIGURING

    if _ZERO_CONFIGURING:
        return

    _ZERO_CONFIGURING = True
    try:
        _install_default_metadata()
        root_logger = logging.getLogger()
        if root_logger.handlers:
            return

        zero_config_kwargs: dict[str, Any] = {
            "format": None,
            "level": _ZERO_CONFIG_LEVEL,
            "handlers": [
                _make_console_handler(
                    stream=None,
                    show_icon=False,
                    show_level=True,
                    show_path=False,
                    show_time=False,
                    boxes=False,
                    rich_tracebacks=True,
                    markup=True,
                )
            ],
        }
        logging.basicConfig(**zero_config_kwargs)
    finally:
        _ZERO_CONFIGURING = False


def _get_or_create_tuned_logger(name: str) -> TunedLogger:
    manager = logging.getLogger().manager
    existing = manager.loggerDict.get(name)

    if isinstance(existing, logging.Logger):
        logger = existing
    else:
        previous_logger_class = manager.loggerClass
        manager.loggerClass = TunedLogger
        try:
            logger = logging.getLogger(name)
        finally:
            manager.loggerClass = previous_logger_class

    if not isinstance(logger, TunedLogger):
        raise ValueError(
            f"Logger {name!r} already exists as {type(logger).__name__}; expected TunedLogger"
        )

    return logger


def _install_tuning_metadata(level_specs: list[LevelSpec], prompt_spec: PromptSpec) -> None:
    global _ROOT_PROMPT_SPEC

    register_level_specs(level_specs)
    install_dynamic_level_methods(TunedLogger, level_specs)
    _ROOT_PROMPT_SPEC = prompt_spec


def _prepare_configured_tuned_loggers(logging_config: dict[str, Any]) -> None:
    loggers = logging_config.get("loggers")
    if not isinstance(loggers, dict):
        return

    manager = logging.getLogger().manager
    for name in loggers:
        existing = manager.loggerDict.get(name)
        if existing is None or not isinstance(existing, logging.Logger):
            _get_or_create_tuned_logger(name)


def _close_logger_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def _first_color_handler(logger: logging.Logger) -> TunedHandler | None:
    current: logging.Logger | None = logger
    while current is not None:
        for handler in current.handlers:
            if isinstance(handler, TunedHandler):
                return handler

        if not current.propagate:
            break
        current = current.parent

    return None


__all__ = [
    "TunedLogger",
    "TunedHandler",
    "LevelSpec",
    "PromptSpec",
    "ISO_FORMAT",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_BACKUP_COUNT",
    "getLogger",
    "export",
    "addLevel",
    "basicConfig",
    "basicConfigFromYaml",
]
