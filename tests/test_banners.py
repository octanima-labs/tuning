from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from rich import box as rich_box
from rich.box import Box
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

import tuning
import tuning._banners as banners_module


def _write_banners(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf8")


def _set_console_width(monkeypatch: pytest.MonkeyPatch, width: int) -> None:
    def console_factory() -> Console:
        return Console(width=width, color_system=None)

    monkeypatch.setattr(banners_module, "Console", console_factory)


class _RecordingConsole:
    def __init__(self, width: int = 80) -> None:
        self.width = width
        self.renderables: list[object] = []

    def print(self, renderable: object) -> None:
        self.renderables.append(renderable)


def _record_console(monkeypatch: pytest.MonkeyPatch, width: int = 80) -> _RecordingConsole:
    console = _RecordingConsole(width=width)
    monkeypatch.setattr(banners_module, "Console", lambda: console)
    return console


def test_banner_is_available_from_top_level_package() -> None:
    assert tuning.banner is banners_module.banner


def test_banner_prints_named_banner_from_explicit_file_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_console_width(monkeypatch, 80)
    banner_path = tmp_path / "my-banners.txt"
    expected = "\nTUNING\n"
    _write_banners(
        banner_path,
        "### first\nnot selected\n### second\n\nTUNING\n###\n",
    )

    selected = tuning.banner(banner_path, name="second")

    output = capsys.readouterr().out

    assert selected == expected
    assert "TUNING" in output


def test_banner_applies_custom_panel_styles_and_padding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nSTYLED\n")

    selected = tuning.banner(
        banner_path,
        border_style="red",
        text_style="green",
        padding=(1, 2),
    )

    assert selected == "STYLED\n"
    assert len(console.renderables) == 1
    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.border_style == "red"
    assert panel.padding == (1, 2)
    assert isinstance(panel.renderable, Text)
    assert panel.renderable.style == "green"


def test_banner_applies_named_box_case_insensitively(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nBOXED\n")

    selected = tuning.banner(banner_path, box="rounded")

    assert selected == "BOXED\n"
    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.box is rich_box.ROUNDED


def test_banner_applies_mega_bold_box(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nMEGA\n")

    tuning.banner(banner_path, box="MEGA_BOLD")

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.box is banners_module.MEGA_BOLD


def test_banner_accepts_box_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nOBJECT\n")
    custom_box = Box("┌─┬┐\n│ ││\n├─┼┤\n│ ││\n├─┼┤\n├─┼┤\n│ ││\n└─┴┘\n")

    tuning.banner(banner_path, box=custom_box)

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.box is custom_box


def test_banner_applies_panel_background_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nBACKGROUND\n")

    tuning.banner(banner_path, background_style="on blue")

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.style == "on blue"


def test_banner_defaults_to_independent_random_styles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nRANDOM\n")
    choices = iter(["red", "blue"])
    monkeypatch.setattr(banners_module.random, "choice", lambda _: next(choices))

    tuning.banner(banner_path)

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.border_style == "bold red"
    assert isinstance(panel.renderable, Text)
    assert panel.renderable.style == "bold blue"


def test_banner_can_render_without_border_but_with_padding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nPLAIN\n")

    selected = tuning.banner(
        banner_path,
        border_style="red",
        text_style="cyan",
        padding=(1, 2, 3, 4),
        border=False,
    )

    assert selected == "PLAIN\n"
    assert len(console.renderables) == 1
    renderable = console.renderables[0]
    assert isinstance(renderable, Padding)
    assert (renderable.top, renderable.right, renderable.bottom, renderable.left) == (1, 2, 3, 4)
    assert isinstance(renderable.renderable, Text)
    assert renderable.renderable.style == "cyan"


def test_banner_applies_borderless_background_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _record_console(monkeypatch)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nPLAIN\n")

    tuning.banner(banner_path, border=False, background_style="on magenta")

    renderable = console.renderables[0]
    assert isinstance(renderable, Padding)
    assert renderable.style == "on magenta"


def test_banner_accepts_directory_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 80)
    _write_banners(tmp_path / "banners.txt", "### only\nDIRECTORY\n")

    assert tuning.banner(tmp_path) == "DIRECTORY\n"


def test_banner_discovers_nearest_banners_file_from_calling_file(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[1]
    app_dir = tmp_path / "app"
    nested_dir = app_dir / "nested"
    nested_dir.mkdir(parents=True)
    _write_banners(app_dir / "banners.txt", "### only\nDISCOVERED\n")
    script_path = nested_dir / "run.py"
    script_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(repo_root)!r})\n"
        "import tuning\n"
        "selected = tuning.banner()\n"
        "print('RETURN=' + repr(selected))\n",
        encoding="utf8",
    )

    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "DISCOVERED" in result.stdout
    assert "RETURN='DISCOVERED\\n'" in result.stdout


def test_banner_discovers_from_cwd_when_caller_has_no_file(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[1]
    _write_banners(tmp_path / "banners.txt", "### only\nFROM CWD\n")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            f"sys.path.insert(0, {str(repo_root)!r}); "
            "import tuning; "
            "selected = tuning.banner(); "
            "print('RETURN=' + repr(selected))",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "FROM CWD" in result.stdout
    assert "RETURN='FROM CWD\\n'" in result.stdout


def test_banner_randomly_selects_only_fitting_banners(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 20)
    banner_path = tmp_path / "banners.txt"
    _write_banners(
        banner_path,
        "### too_wide\nTHIS BANNER IS TOO WIDE\n### small\nSMALL\n",
    )

    def choice(options: Sequence[str]) -> str:
        assert options == ["SMALL\n"]
        return options[0]

    monkeypatch.setattr(banners_module.random, "choice", choice)

    assert tuning.banner(banner_path, border_style="red", text_style="blue") == "SMALL\n"


def test_banner_returns_none_when_no_banner_fits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_console_width(monkeypatch, 9)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nTOO WIDE\n")

    selected = tuning.banner(banner_path)
    output = capsys.readouterr().out

    assert selected is None
    assert "We" in output
    assert "tight" in output


def test_banner_named_too_wide_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 9)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### wide\nTOO WIDE\n### small\nOK\n")

    assert tuning.banner(banner_path, name="wide") is None


def test_banner_padding_affects_terminal_fit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 9)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nABCD\n")

    assert tuning.banner(banner_path, padding=(0, 2)) is None
    assert tuning.banner(banner_path, padding=(0, 1)) == "ABCD\n"


def test_banner_border_affects_terminal_fit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 5)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nABCD\n")

    assert tuning.banner(banner_path) is None
    assert tuning.banner(banner_path, border=False) == "ABCD\n"


@pytest.mark.parametrize(
    "padding",
    [(), (1, 2, 3), (1, 2, 3, 4, 5), (-1,), ("1",)],
)
def test_banner_rejects_invalid_padding(tmp_path: Path, padding: tuple[object, ...]) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n")

    with pytest.raises(ValueError, match="padding"):
        tuning.banner(banner_path, padding=padding)  # type: ignore[arg-type]


def test_banner_rejects_non_boolean_border(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n")

    with pytest.raises(ValueError, match="border"):
        tuning.banner(banner_path, border="false")  # type: ignore[arg-type]


def test_banner_rejects_invalid_box_name(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n")

    with pytest.raises(ValueError, match="box"):
        tuning.banner(banner_path, box="not_a_box")


def test_banner_validates_box_when_border_is_false(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n")

    with pytest.raises(ValueError, match="box"):
        tuning.banner(banner_path, border=False, box="not_a_box")


def test_banner_raises_for_missing_discovered_banner_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Banner file not defined"):
        tuning.banner()


def test_banner_raises_key_error_for_missing_name(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n")

    with pytest.raises(KeyError):
        tuning.banner(banner_path, name="missing")


def test_banner_raises_for_invalid_banner_name(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### Not_Valid\nCONTENT\n")

    with pytest.raises(ValueError, match="Invalid banner name"):
        tuning.banner(banner_path)


def test_banner_raises_for_duplicate_banner_name(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### same\nONE\n### same\nTWO\n")

    with pytest.raises(ValueError, match="Duplicate banner name"):
        tuning.banner(banner_path)


def test_banner_allows_final_empty_marker_terminator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_console_width(monkeypatch, 80)
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### only\nCONTENT\n###\n")

    assert tuning.banner(banner_path) == "CONTENT\n"


def test_banner_rejects_middle_empty_marker(tmp_path: Path) -> None:
    banner_path = tmp_path / "banners.txt"
    _write_banners(banner_path, "### first\nONE\n###\nTWO\n")

    with pytest.raises(ValueError, match="Empty banner marker"):
        tuning.banner(banner_path)
