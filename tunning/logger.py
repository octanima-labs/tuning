from __future__ import annotations

import json
import logging
import logging.config
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import bitmath
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "conf.yml"
_BUILTIN_LEVELS = {
    "NOTSET": logging.NOTSET,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
_ALIASED_LEVEL_NAMES = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}
_LEVEL_SPECS_BY_NAME: dict[str, "LevelSpec"] = {}
_LEVEL_SPECS_BY_CODE: dict[int, "LevelSpec"] = {}
_DYNAMIC_METHODS: dict[str, int] = {}


@dataclass(frozen=True)
class LevelSpec:
    name: str
    code: int
    symbol: str | None = None
    icon: str | None = None
    style: str | None = None


@dataclass(frozen=True)
class PromptSpec:
    symbol: str | None = None
    icon: str | None = None
    style: str | None = None


def _load_yaml(path_value: str | Path) -> dict[str, Any]:
    path = Path(path_value)
    with path.open("r", encoding="utf8") as file_handle:
        data = yaml.safe_load(file_handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in YAML config: {path}")

    return data


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = deepcopy(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    return deepcopy(override)


def _normalize_level_name(raw_name: str) -> str:
    return raw_name.strip().upper()


def _normalize_method_name(level_name: str) -> str:
    return level_name.lower().replace("-", "_")


def _validate_symbol(symbol: str | None, *, field_name: str) -> str | None:
    if symbol is None:
        return None

    if not isinstance(symbol, str) or not symbol:
        raise ValueError(f"{field_name} must be a non-empty string when provided")

    if len(symbol) > 3:
        raise ValueError(f"{field_name} must be at most 3 characters")

    return symbol


def _validate_style(style: str | None, *, field_name: str) -> str | None:
    if style is None:
        return None

    if not isinstance(style, str):
        raise ValueError(f"{field_name} must be a string when provided")

    Style.parse(style)
    return style


def _coerce_level_code(level_name: str, code: Any) -> int:
    if isinstance(code, bool):
        raise ValueError(f"Level {level_name} code must be an integer")

    if isinstance(code, int):
        return code

    if isinstance(code, str) and code.strip().isdigit():
        return int(code.strip())

    raise ValueError(f"Level {level_name} code must be an integer")


def _parse_level_specs(levels_config: dict[str, Any]) -> list[LevelSpec]:
    if not isinstance(levels_config, dict):
        raise ValueError("levels must be a mapping")

    specs: list[LevelSpec] = []
    seen_names: set[str] = set()
    seen_codes: set[int] = set()

    for raw_name, raw_spec in levels_config.items():
        if not isinstance(raw_spec, dict):
            raise ValueError(f"Level {raw_name} must be configured as a mapping")

        name = _normalize_level_name(raw_name)
        if name == "INPUT":
            raise ValueError("Use the top-level prompt section instead of levels.INPUT")

        if name in _ALIASED_LEVEL_NAMES:
            canonical_name = _ALIASED_LEVEL_NAMES[name]
            raise ValueError(f"Use {canonical_name} instead of {name} in levels")

        code = _coerce_level_code(name, raw_spec.get("code"))
        expected_builtin_code = _BUILTIN_LEVELS.get(name)
        if expected_builtin_code is not None and code != expected_builtin_code:
            raise ValueError(
                f"Built-in level {name} must use stdlib code {expected_builtin_code}, not {code}"
            )

        if name in seen_names:
            raise ValueError(f"Duplicate level name: {name}")
        if code in seen_codes:
            raise ValueError(f"Duplicate level code: {code}")

        symbol = _validate_symbol(raw_spec.get("symbol"), field_name=f"levels.{raw_name}.symbol")
        icon = raw_spec.get("icon")
        if icon is not None and not isinstance(icon, str):
            raise ValueError(f"levels.{raw_name}.icon must be a string when provided")

        style = _validate_style(raw_spec.get("style"), field_name=f"levels.{raw_name}.style")

        seen_names.add(name)
        seen_codes.add(code)
        specs.append(LevelSpec(name=name, code=code, symbol=symbol, icon=icon, style=style))

    return specs


def _parse_prompt_spec(prompt_config: dict[str, Any]) -> PromptSpec:
    if not isinstance(prompt_config, dict):
        raise ValueError("prompt must be a mapping")

    symbol = _validate_symbol(prompt_config.get("symbol"), field_name="prompt.symbol")
    icon = prompt_config.get("icon")
    if icon is not None and not isinstance(icon, str):
        raise ValueError("prompt.icon must be a string when provided")

    style = _validate_style(prompt_config.get("style"), field_name="prompt.style")
    return PromptSpec(symbol=symbol, icon=icon, style=style)


def _register_level_spec(spec: LevelSpec) -> None:
    existing_by_name = _LEVEL_SPECS_BY_NAME.get(spec.name)
    if existing_by_name and existing_by_name != spec:
        raise ValueError(f"Level {spec.name} is already registered with a different definition")

    existing_by_code = _LEVEL_SPECS_BY_CODE.get(spec.code)
    if existing_by_code and existing_by_code != spec:
        raise ValueError(f"Level code {spec.code} is already registered for {existing_by_code.name}")

    known_levels = logging.getLevelNamesMapping()
    if spec.name in known_levels and known_levels[spec.name] != spec.code:
        raise ValueError(
            f"Level {spec.name} is already registered with code {known_levels[spec.name]}"
        )

    known_name = logging.getLevelName(spec.code)
    if isinstance(known_name, str) and not known_name.startswith("Level ") and known_name != spec.name:
        raise ValueError(f"Level code {spec.code} is already reserved for {known_name}")

    if spec.name not in _BUILTIN_LEVELS:
        logging.addLevelName(spec.code, spec.name)

    _LEVEL_SPECS_BY_NAME[spec.name] = spec
    _LEVEL_SPECS_BY_CODE[spec.code] = spec


def _make_level_method(level_code: int, level_name: str, method_name: str):
    def log_for_level(self: "TunnedLogger", msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(level_code):
            self._log(level_code, msg, args, **kwargs)

    log_for_level.__name__ = method_name
    log_for_level.__qualname__ = f"TunnedLogger.{method_name}"
    log_for_level.__doc__ = f"Log a message with the {level_name} level."
    return log_for_level


def _install_dynamic_level_methods(specs: list[LevelSpec]) -> None:
    for spec in specs:
        if spec.name in _BUILTIN_LEVELS:
            continue

        method_name = _normalize_method_name(spec.name)
        existing_level = _DYNAMIC_METHODS.get(method_name)
        if existing_level is not None:
            if existing_level != spec.code:
                raise ValueError(
                    f"Method {method_name} is already bound to level {existing_level}, not {spec.code}"
                )
            continue

        if hasattr(TunnedLogger, method_name):
            raise ValueError(f"Cannot create dynamic method {method_name}: name already exists")

        setattr(TunnedLogger, method_name, _make_level_method(spec.code, spec.name, method_name))
        _DYNAMIC_METHODS[method_name] = spec.code


def _resolve_handler_factory(handler_config: dict[str, Any]) -> Any:
    return handler_config.get("()") or handler_config.get("class")


def _is_custom_rich_handler(handler_config: dict[str, Any]) -> bool:
    factory = _resolve_handler_factory(handler_config)
    if factory is TunnedHandler:
        return True

    if isinstance(factory, str):
        return factory in {
            f"{TunnedHandler.__module__}.{TunnedHandler.__qualname__}",
            "tunning.TunnedHandler",
        }

    return False


def _parse_size_to_bytes(raw_value: str) -> int:
    try:
        size = bitmath.parse_string(raw_value)
    except ValueError as error:
        raise ValueError(f"Invalid maxBytes value: {raw_value}") from error

    return int(size.bytes)


def _normalize_handler_config(handler_name: str, handler_config: dict[str, Any]) -> None:
    if "show_icon" in handler_config:
        if not _is_custom_rich_handler(handler_config):
            raise ValueError(f"Handler {handler_name} uses show_icon but is not a TunnedHandler")

        if not isinstance(handler_config["show_icon"], bool):
            raise ValueError(f"handlers.{handler_name}.show_icon must be a boolean")

    if "maxBytes" in handler_config and isinstance(handler_config["maxBytes"], str):
        handler_config["maxBytes"] = _parse_size_to_bytes(handler_config["maxBytes"])

    filename = handler_config.get("filename")
    if filename is not None:
        Path(filename).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _select_logger_config(config: dict[str, Any], logger_name: str) -> dict[str, Any]:
    loggers = config.get("loggers")
    root_config = config.get("root")

    if loggers is not None and not isinstance(loggers, dict):
        raise ValueError("loggers must be a mapping when provided")

    if loggers:
        extra_loggers = [name for name in loggers if name != logger_name]
        if extra_loggers:
            raise ValueError(
                "v1 only supports configuring the requested logger name; "
                f"unexpected entries: {', '.join(extra_loggers)}"
            )

    if loggers and logger_name in loggers:
        logger_config = deepcopy(loggers[logger_name])
    elif root_config is not None:
        logger_config = deepcopy(root_config)
    else:
        raise ValueError("Config must define either root or the requested logger entry")

    if not isinstance(logger_config, dict):
        raise ValueError("Logger configuration must be a mapping")

    logger_config.setdefault("propagate", False)
    return logger_config


def _normalize_logging_config(config: dict[str, Any], logger_name: str) -> dict[str, Any]:
    normalized = deepcopy(config)
    normalized.pop("levels", None)
    normalized.pop("prompt", None)

    version = normalized.get("version", 1)
    if version != 1:
        raise ValueError(f"Unsupported logging config version: {version}")

    normalized["version"] = 1
    normalized["disable_existing_loggers"] = False

    handlers = normalized.get("handlers", {})
    if not isinstance(handlers, dict) or not handlers:
        raise ValueError("Config must define at least one handler")

    for handler_name, handler_config in handlers.items():
        if not isinstance(handler_config, dict):
            raise ValueError(f"Handler {handler_name} must be configured as a mapping")
        _normalize_handler_config(handler_name, handler_config)

    logger_config = _select_logger_config(normalized, logger_name)
    normalized.pop("root", None)
    normalized["loggers"] = {logger_name: logger_config}

    return normalized


def _build_signature(
    normalized_config: dict[str, Any],
    level_specs: list[LevelSpec],
    prompt_spec: PromptSpec,
) -> str:
    payload = {
        "config": normalized_config,
        "levels": [asdict(spec) for spec in level_specs],
        "prompt": asdict(prompt_spec),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _get_existing_logger(name: str) -> logging.Logger | logging.PlaceHolder | None:
    return logging.getLogger().manager.loggerDict.get(name)


def _get_or_create_tunned_logger(name: str) -> "TunnedLogger":
    manager = logging.getLogger().manager
    existing = manager.loggerDict.get(name)

    if isinstance(existing, logging.Logger):
        logger = existing
    else:
        previous_logger_class = manager.loggerClass
        manager.loggerClass = TunnedLogger
        try:
            logger = logging.getLogger(name)
        finally:
            manager.loggerClass = previous_logger_class

    if not isinstance(logger, TunnedLogger):
        raise ValueError(
            f"Logger {name!r} already exists as {type(logger).__name__}; expected TunnedLogger"
        )

    return logger


def _close_logger_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def _first_color_handler(logger: logging.Logger) -> "TunnedHandler | None":
    for handler in logger.handlers:
        if isinstance(handler, TunnedHandler):
            return handler
    return None


def _render_prompt_prefix(prompt_spec: PromptSpec, *, show_icon: bool) -> Text:
    if show_icon and prompt_spec.icon:
        prefix = prompt_spec.icon
    elif prompt_spec.symbol:
        prefix = prompt_spec.symbol
    else:
        prefix = ">"

    style = prompt_spec.style or ""
    if style:
        return Text.styled(prefix, style)

    return Text(prefix)


class TunnedHandler(RichHandler):
    def __init__(self, *args: Any, show_icon: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.show_icon = show_icon

    def get_level_text(self, record: logging.LogRecord) -> Text:
        spec = _LEVEL_SPECS_BY_NAME.get(record.levelname)
        if spec is None:
            prefix = f"[{record.levelname}]"
            style = f"logging.level.{record.levelname.lower()}"
        else:
            if self.show_icon and spec.icon:
                prefix = spec.icon
            elif spec.symbol:
                prefix = spec.symbol
            else:
                prefix = f"[{record.levelname}]"

            style = spec.style or f"logging.level.{record.levelname.lower()}"

        rendered_prefix = prefix if len(prefix) >= 8 else prefix.ljust(8)
        return Text.styled(rendered_prefix, style)


class TunnedLogger(logging.Logger):
    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self._tunning_signature: str | None = None
        self._prompt_spec = PromptSpec()

    @classmethod
    def from_yaml(
        cls,
        config_path: str | Path,
        *,
        name: str = "app",
        defaults_path: str | Path | None = None,
        force: bool = False,
    ) -> "TunnedLogger":
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Logger name must be a non-empty string")

        base_config = _load_yaml(defaults_path or _DEFAULT_CONFIG_PATH)
        override_config = _load_yaml(config_path)
        merged_config = _deep_merge(base_config, override_config)

        level_specs = _parse_level_specs(merged_config.get("levels", {}))
        prompt_spec = _parse_prompt_spec(merged_config.get("prompt", {}))
        normalized_config = _normalize_logging_config(merged_config, name)
        signature = _build_signature(normalized_config, level_specs, prompt_spec)

        logger = _get_or_create_tunned_logger(name)
        existing_signature = logger._tunning_signature
        if existing_signature == signature and not force:
            return logger

        if existing_signature and existing_signature != signature and not force:
            raise ValueError(
                f"TunnedLogger {name!r} is already configured with a different config; use force=True"
            )

        if existing_signature is None and logger.handlers and not force:
            raise ValueError(
                f"TunnedLogger {name!r} already has handlers but is not managed by from_yaml; use force=True"
            )

        for spec in level_specs:
            _register_level_spec(spec)
        _install_dynamic_level_methods(level_specs)

        if force:
            _close_logger_handlers(logger)

        logging.config.dictConfig(normalized_config)
        configured_logger = logging.getLogger(name)
        if not isinstance(configured_logger, TunnedLogger):
            raise ValueError(f"Configured logger {name!r} is not a TunnedLogger")

        configured_logger._tunning_signature = signature
        configured_logger._prompt_spec = prompt_spec
        return configured_logger

    def prompt(
        self,
        message: str,
        *,
        password: bool = False,
        markup: bool | None = None,
    ) -> str:
        if not isinstance(message, str):
            raise ValueError("Prompt message must be a string")

        handler = _first_color_handler(self)
        console = handler.console if handler else Console()
        show_icon = handler.show_icon if handler else False
        use_markup = handler.markup if handler and markup is None else bool(markup)

        prefix = _render_prompt_prefix(self._prompt_spec, show_icon=show_icon)
        message_text = Text.from_markup(message) if use_markup else Text(message)
        prompt_text = Text.assemble(prefix, " ", message_text, " ")
        return console.input(prompt_text, markup=False, password=password)


__all__ = ["TunnedLogger", "TunnedHandler", "LevelSpec", "PromptSpec"]
