from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LevelSpec:
    """Metadata attached to a logging level.

    Attributes:
        name: Level name, for example `INFO` or `SUCCESS`.
        code: Numeric stdlib logging level code.
        symbol: Compact text prefix used when icons are disabled.
        icon: Icon prefix used when `show_icon=True`.
        style: Rich style applied to console level prefixes and messages.
    """

    name: str
    code: int
    symbol: str | None = None
    icon: str | None = None
    style: str | None = None


@dataclass(frozen=True)
class PromptSpec:
    """Metadata used to render styled interactive prompts.

    Attributes:
        symbol: Prompt prefix used when icons are disabled.
        icon: Prompt prefix used when icons are enabled.
        style: Rich style applied to the prompt prefix and question text.
    """

    symbol: str | None = None
    icon: str | None = None
    style: str | None = None
