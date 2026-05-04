from __future__ import annotations

import logging
from typing import Any

from rich.style import Style

from tunning._models import LevelSpec

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
_LEVEL_SPECS_BY_NAME: dict[str, LevelSpec] = {}
_LEVEL_SPECS_BY_CODE: dict[int, LevelSpec] = {}
_DYNAMIC_METHODS: dict[str, int] = {}


def get_level_spec(level_name: str) -> LevelSpec | None:
    return _LEVEL_SPECS_BY_NAME.get(level_name)


def parse_level_specs(levels_config: dict[str, Any]) -> list[LevelSpec]:
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

        symbol = validate_symbol(raw_spec.get("symbol"), field_name=f"levels.{raw_name}.symbol")
        icon = raw_spec.get("icon")
        if icon is not None and not isinstance(icon, str):
            raise ValueError(f"levels.{raw_name}.icon must be a string when provided")

        style = validate_style(raw_spec.get("style"), field_name=f"levels.{raw_name}.style")

        seen_names.add(name)
        seen_codes.add(code)
        specs.append(LevelSpec(name=name, code=code, symbol=symbol, icon=icon, style=style))

    return specs


def register_level_specs(specs: list[LevelSpec]) -> None:
    for spec in specs:
        _register_level_spec(spec)


def install_dynamic_level_methods(logger_cls: type[logging.Logger], specs: list[LevelSpec]) -> None:
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

        if hasattr(logger_cls, method_name):
            raise ValueError(f"Cannot create dynamic method {method_name}: name already exists")

        setattr(logger_cls, method_name, _make_level_method(spec.code, spec.name, method_name))
        _DYNAMIC_METHODS[method_name] = spec.code


def validate_symbol(symbol: str | None, *, field_name: str) -> str | None:
    if symbol is None:
        return None

    if not isinstance(symbol, str) or not symbol:
        raise ValueError(f"{field_name} must be a non-empty string when provided")

    if len(symbol) > 3:
        raise ValueError(f"{field_name} must be at most 3 characters")

    return symbol


def validate_style(style: str | None, *, field_name: str) -> str | None:
    if style is None:
        return None

    if not isinstance(style, str):
        raise ValueError(f"{field_name} must be a string when provided")

    Style.parse(style)
    return style


def _normalize_level_name(raw_name: str) -> str:
    return raw_name.strip().upper()


def _normalize_method_name(level_name: str) -> str:
    return level_name.lower().replace("-", "_")


def _coerce_level_code(level_name: str, code: Any) -> int:
    if isinstance(code, bool):
        raise ValueError(f"Level {level_name} code must be an integer")

    if isinstance(code, int):
        return code

    if isinstance(code, str) and code.strip().isdigit():
        return int(code.strip())

    raise ValueError(f"Level {level_name} code must be an integer")


def _register_level_spec(spec: LevelSpec) -> None:
    existing_by_name = _LEVEL_SPECS_BY_NAME.get(spec.name)
    if existing_by_name and existing_by_name != spec:
        raise ValueError(f"Level {spec.name} is already registered with a different definition")

    existing_by_code = _LEVEL_SPECS_BY_CODE.get(spec.code)
    if existing_by_code and existing_by_code != spec:
        raise ValueError(
            f"Level code {spec.code} is already registered for {existing_by_code.name}"
        )

    known_levels = logging.getLevelNamesMapping()
    if spec.name in known_levels and known_levels[spec.name] != spec.code:
        raise ValueError(
            f"Level {spec.name} is already registered with code {known_levels[spec.name]}"
        )

    known_name = logging.getLevelName(spec.code)
    if (
        isinstance(known_name, str)
        and not known_name.startswith("Level ")
        and known_name != spec.name
    ):
        raise ValueError(f"Level code {spec.code} is already reserved for {known_name}")

    if spec.name not in _BUILTIN_LEVELS:
        logging.addLevelName(spec.code, spec.name)

    _LEVEL_SPECS_BY_NAME[spec.name] = spec
    _LEVEL_SPECS_BY_CODE[spec.code] = spec


def _make_level_method(level_code: int, level_name: str, method_name: str):
    def log_for_level(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(level_code):
            kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
            self._log(level_code, msg, args, **kwargs)

    log_for_level.__name__ = method_name
    log_for_level.__qualname__ = f"TunnedLogger.{method_name}"
    log_for_level.__doc__ = f"Log a message with the {level_name} level."
    return log_for_level
