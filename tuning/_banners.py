from __future__ import annotations


import inspect
import random
import re
from pathlib import Path
from typing import TypeAlias

from rich.cells import cell_len
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.box import Box


_BANNER_FILENAME = "banners.txt"
_BANNER_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_FALLBACK_MESSAGE = "We could display a beautiful banner here, but the terminal is too tight :("
_RANDOM_STYLE_COLORS = (
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "bright_black",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
    "bright_white",
)
MEGA_BOLD = Box(
    "████\n"
    "█  █\n"
    "████\n"
    "█  █\n"
    "████\n"
    "█  █\n"
    "████\n"
    "████\n"
)
_PaddingSpec: TypeAlias = tuple[int] | tuple[int, int] | tuple[int, int, int, int]



def banner(
    path: str | Path | None = None,
    name: str | None = None,
    *,
    border_style: str | None = None,
    text_style: str | None = None,
    padding: tuple[int] | tuple[int, int] | tuple[int, int, int, int] = (0, 0),
    border: bool = True,
) -> str | None:
    """Print an application banner from a banner file.

    Banner files contain one or more sections marked by `### banner_name`.
    When `path` is omitted, `banners.txt` is discovered by walking upward from
    the calling file's directory. If the caller has no file, discovery starts
    from the current working directory.

    Args:
        path: Banner file path, directory containing `banners.txt`, or `None`
            to discover `banners.txt` from the caller location.
        name: Optional banner name. If omitted, a random banner that fits the
            current terminal width is selected.
        border_style: Rich style for the panel border. If omitted, a random
            bold color is used.
        text_style: Rich style for the banner text. If omitted, a random bold
            color is used.
        padding: Rich-compatible padding tuple. Accepts `(all,)`,
            `(vertical, horizontal)`, or `(top, right, bottom, left)`.
        border: Render the banner inside a Rich panel when true. When false,
            only styled text and padding are rendered.

    Returns:
        The exact banner body printed, or `None` when no banner fits the
        terminal and the fallback message is printed instead.

    Raises:
        ValueError: If no banner file can be discovered, or if the banner file
            is malformed.
        FileNotFoundError: If an explicit banner file path does not exist.
        KeyError: If `name` is provided but no matching banner exists.
    """
    resolved_padding = _normalize_padding(padding)
    if not isinstance(border, bool):
        raise ValueError("border must be a boolean")
    resolved_border_style = border_style or _random_style()
    resolved_text_style = text_style or _random_style()
    banner_path = _resolve_banner_path(path)
    banners = _parse_banners(banner_path.read_text(encoding="utf8"), banner_path)
    console = Console()
    selected_banner = _select_banner(banners, name, console.width, resolved_padding, border)

    if selected_banner is None:
        _print_banner(
            _FALLBACK_MESSAGE,
            console,
            border_style=resolved_border_style,
            text_style=resolved_text_style,
            padding=padding,
            border=border,
        )
        return None

    _print_banner(
        selected_banner,
        console,
        border_style=resolved_border_style,
        text_style=resolved_text_style,
        padding=padding,
        border=border,
    )
    return selected_banner


def _random_style() -> str:
    return f"bold {random.choice(_RANDOM_STYLE_COLORS)}"


def _resolve_banner_path(path: str | Path | None) -> Path:
    if path is None:
        return _discover_banner_path()

    resolved_path = Path(path).expanduser()
    if resolved_path.is_dir():
        resolved_path = resolved_path / _BANNER_FILENAME
    return resolved_path


def _discover_banner_path() -> Path:
    start_dir = _caller_directory() or Path.cwd()
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / _BANNER_FILENAME
        if candidate.is_file():
            return candidate

    raise ValueError("Banner file not defined")


def _caller_directory() -> Path | None:
    current_file = Path(__file__).resolve()
    frame = inspect.currentframe()
    while frame is not None:
        filename = frame.f_code.co_filename
        if filename and not filename.startswith("<"):
            candidate = Path(filename).resolve()
            if candidate != current_file:
                return candidate.parent
        frame = frame.f_back

    return None


def _parse_banners(content: str, source: Path) -> dict[str, str]:
    banners: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    lines = content.splitlines(keepends=True)

    for index, line in enumerate(lines):
        if not line.startswith("###"):
            if current_name is not None:
                current_lines.append(line)
            elif line.strip():
                raise ValueError(f"Banner content must start with a marker: {source}")
            continue

        current_name = _store_banner(banners, current_name, current_lines, source)
        current_lines = []
        marker_name = line[3:].strip()
        if not marker_name:
            if any(remaining_line.strip() for remaining_line in lines[index + 1 :]):
                raise ValueError(f"Empty banner marker must terminate the file: {source}")
            current_name = None
            break
        if _BANNER_NAME_PATTERN.fullmatch(marker_name) is None:
            raise ValueError(f"Invalid banner name {marker_name!r}: {source}")
        current_name = marker_name

    _store_banner(banners, current_name, current_lines, source)
    if not banners:
        raise ValueError(f"No banners defined: {source}")

    return banners


def _store_banner(
    banners: dict[str, str],
    name: str | None,
    lines: list[str],
    source: Path,
) -> str | None:
    if name is None:
        return None
    if name in banners:
        raise ValueError(f"Duplicate banner name {name!r}: {source}")

    banner_text = "".join(lines)
    if not banner_text:
        raise ValueError(f"Banner {name!r} has no content: {source}")

    banners[name] = banner_text
    return None


def _select_banner(
    banners: dict[str, str],
    name: str | None,
    console_width: int,
    padding: tuple[int, int, int, int],
    border: bool,
) -> str | None:
    if name is not None:
        if name not in banners:
            raise KeyError(name)
        selected_banner = banners[name]
        if _banner_fits(selected_banner, console_width, padding, border):
            return selected_banner
        return None

    if len(banners) == 1:
        selected_banner = next(iter(banners.values()))
        if _banner_fits(selected_banner, console_width, padding, border):
            return selected_banner
        return None

    fitting_banners = [
        banner_text
        for banner_text in banners.values()
        if _banner_fits(banner_text, console_width, padding, border)
    ]
    if not fitting_banners:
        return None

    return random.choice(fitting_banners)


def _banner_fits(
    banner_text: str,
    console_width: int,
    padding: tuple[int, int, int, int],
    border: bool,
) -> bool:
    return _banner_width(banner_text) + _horizontal_overhead(padding, border) <= console_width


def _banner_width(banner_text: str) -> int:
    return max((cell_len(line.rstrip("\r\n")) for line in banner_text.splitlines()), default=0)


def _horizontal_overhead(padding: tuple[int, int, int, int], border: bool) -> int:
    _, right, _, left = padding
    border_width = 2 if border else 0
    return border_width + right + left


def _normalize_padding(padding: _PaddingSpec) -> tuple[int, int, int, int]:
    if not isinstance(padding, tuple):
        raise ValueError("padding must be a tuple of 1, 2, or 4 non-negative integers")
    if len(padding) not in {1, 2, 4}:
        raise ValueError("padding must be a tuple of 1, 2, or 4 non-negative integers")
    if any(not isinstance(value, int) or value < 0 for value in padding):
        raise ValueError("padding must be a tuple of 1, 2, or 4 non-negative integers")

    if len(padding) == 1:
        top = right = bottom = left = padding[0]
    elif len(padding) == 2:
        top = bottom = padding[0]
        right = left = padding[1]
    else:
        top, right, bottom, left = padding

    return top, right, bottom, left


def _print_banner(
    banner_text: str,
    console: Console,
    *,
    border_style: str,
    text_style: str,
    padding: _PaddingSpec,
    border: bool,
) -> None:
    text = Text(banner_text, style=text_style)
    if not border:
        console.print(Padding(text, padding))
        return

    console.print(
        Panel.fit(
            text,
            box=MEGA_BOLD, # TODO: control via param
            border_style=border_style,
            padding=padding,
        )
    )
