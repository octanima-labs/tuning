from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import bitmath
import yaml

from tunning._levels import parse_level_specs
from tunning._models import LevelSpec, PromptSpec
from tunning._prompt import parse_prompt_spec

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "conf.yml"


@dataclass(frozen=True)
class ResolvedConfig:
    logging_config: dict[str, Any]
    level_specs: list[LevelSpec]
    prompt_spec: PromptSpec
    signature: str


@dataclass(frozen=True)
class TunningMetadata:
    level_specs: list[LevelSpec]
    prompt_spec: PromptSpec


def load_tunning_config(
    config_path: str | Path,
    *,
    logger_name: str,
    defaults_path: str | Path | None = None,
) -> ResolvedConfig:
    base_config = _load_yaml(defaults_path or _DEFAULT_CONFIG_PATH)
    override_config = _load_yaml(config_path)
    merged_config = _deep_merge(base_config, override_config)

    level_specs = parse_level_specs(merged_config.get("levels", {}))
    prompt_spec = parse_prompt_spec(merged_config.get("prompt", {}))
    normalized_config = _normalize_named_logging_config(merged_config, logger_name)
    signature = _build_signature(normalized_config, level_specs, prompt_spec)

    return ResolvedConfig(
        logging_config=normalized_config,
        level_specs=level_specs,
        prompt_spec=prompt_spec,
        signature=signature,
    )


def load_tunning_root_config(
    config_path: str | Path | None = None,
    *,
    defaults_path: str | Path | None = None,
) -> ResolvedConfig:
    base_config = _load_yaml(defaults_path or _DEFAULT_CONFIG_PATH)
    if config_path is None:
        merged_config = base_config
    else:
        override_config = _load_yaml(config_path)
        merged_config = _deep_merge(base_config, override_config)

    level_specs = parse_level_specs(merged_config.get("levels", {}))
    prompt_spec = parse_prompt_spec(merged_config.get("prompt", {}))
    normalized_config = _normalize_root_logging_config(merged_config)
    signature = _build_signature(normalized_config, level_specs, prompt_spec)

    return ResolvedConfig(
        logging_config=normalized_config,
        level_specs=level_specs,
        prompt_spec=prompt_spec,
        signature=signature,
    )


def load_tunning_metadata(*, defaults_path: str | Path | None = None) -> TunningMetadata:
    config = _load_yaml(defaults_path or _DEFAULT_CONFIG_PATH)
    return TunningMetadata(
        level_specs=parse_level_specs(config.get("levels", {})),
        prompt_spec=parse_prompt_spec(config.get("prompt", {})),
    )


def export_default_config(path: str | Path, *, force: bool = False) -> Path:
    target_path = Path(path).expanduser()
    if target_path.exists() and not force:
        raise FileExistsError(f"Config file already exists: {target_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(_DEFAULT_CONFIG_PATH.read_text(encoding="utf8"), encoding="utf8")
    return target_path.resolve()


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


def _normalize_named_logging_config(config: dict[str, Any], logger_name: str) -> dict[str, Any]:
    normalized = deepcopy(config)
    normalized.pop("levels", None)
    normalized.pop("prompt", None)

    _normalize_common_logging_config(normalized)

    logger_config = _select_logger_config(normalized, logger_name)
    normalized.pop("root", None)
    normalized["loggers"] = {logger_name: logger_config}

    return normalized


def _normalize_root_logging_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(config)
    normalized.pop("levels", None)
    normalized.pop("prompt", None)

    _normalize_common_logging_config(normalized)

    loggers = normalized.get("loggers")
    if loggers is not None and not isinstance(loggers, dict):
        raise ValueError("loggers must be a mapping when provided")

    root_config = normalized.get("root")
    if root_config is None:
        raise ValueError("Config must define root for basicConfigFromYaml")

    if not isinstance(root_config, dict):
        raise ValueError("Root configuration must be a mapping")

    return normalized


def _normalize_common_logging_config(normalized: dict[str, Any]) -> None:
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


def _normalize_handler_config(handler_name: str, handler_config: dict[str, Any]) -> None:
    for tunning_option in ("show_icon", "boxes"):
        if tunning_option not in handler_config:
            continue

        if not _is_custom_rich_handler(handler_config):
            raise ValueError(
                f"Handler {handler_name} uses {tunning_option} but is not a TunnedHandler"
            )

        if not isinstance(handler_config[tunning_option], bool):
            raise ValueError(f"handlers.{handler_name}.{tunning_option} must be a boolean")

    if "maxBytes" in handler_config and isinstance(handler_config["maxBytes"], str):
        handler_config["maxBytes"] = parse_size_to_bytes(
            handler_config["maxBytes"], field_name="maxBytes"
        )

    filename = handler_config.get("filename")
    if filename is not None:
        Path(filename).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _is_custom_rich_handler(handler_config: dict[str, Any]) -> bool:
    factory = handler_config.get("()") or handler_config.get("class")
    if isinstance(factory, str):
        return factory in {
            "tunning.logger.TunnedHandler",
            "tunning.TunnedHandler",
        }

    return (
        getattr(factory, "__module__", None) == "tunning.logger"
        and getattr(factory, "__qualname__", None) == "TunnedHandler"
    )


def parse_size_to_bytes(raw_value: str, *, field_name: str) -> int:
    try:
        size = bitmath.parse_string(raw_value)
    except ValueError as error:
        raise ValueError(f"Invalid {field_name} value: {raw_value}") from error

    return int(size.bytes)


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
