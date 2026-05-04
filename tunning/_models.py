from __future__ import annotations

from dataclasses import dataclass


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
