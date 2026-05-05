from __future__ import annotations

from typing import Any

from rich.text import Text

from tuning._levels import validate_style, validate_symbol
from tuning._models import PromptSpec


def parse_prompt_spec(prompt_config: dict[str, Any]) -> PromptSpec:
    if not isinstance(prompt_config, dict):
        raise ValueError("prompt must be a mapping")

    symbol = validate_symbol(prompt_config.get("symbol"), field_name="prompt.symbol")
    icon = prompt_config.get("icon")
    if icon is not None and not isinstance(icon, str):
        raise ValueError("prompt.icon must be a string when provided")

    style = validate_style(prompt_config.get("style"), field_name="prompt.style")
    return PromptSpec(symbol=symbol, icon=icon, style=style)


def render_prompt_prefix(prompt_spec: PromptSpec, *, show_icon: bool) -> Text:
    prefix = _select_prompt_prefix(prompt_spec, show_icon=show_icon)
    style = prompt_spec.style or ""
    if style:
        return Text.styled(prefix, style)

    return Text(prefix)


def render_prompt_text(
    prompt_spec: PromptSpec,
    message: str,
    *,
    show_icon: bool,
    markup: bool,
) -> Text:
    prefix = _select_prompt_prefix(prompt_spec, show_icon=show_icon)
    message_text = Text.from_markup(message) if markup else Text(message)
    prompt_text = Text.assemble(prefix, " ", message_text)

    if prompt_spec.style:
        prompt_text.stylize(prompt_spec.style, 0, len(prompt_text))

    prompt_text.append(" ")
    return prompt_text


def _select_prompt_prefix(prompt_spec: PromptSpec, *, show_icon: bool) -> str:
    if show_icon and prompt_spec.icon:
        return prompt_spec.icon
    elif prompt_spec.symbol:
        return prompt_spec.symbol

    return ">"
