"""Display-only Arabic text preparation. NEVER apply this to text that is stored or edited.

Two rendering modes, chosen at start-up by a probe (see app/widgets/textengine.py):

* "reshape" - DEFAULT. The text renderer draws each code point as an isolated letter, in
              left-to-right order (measured on Linux/Kivy 2.3.1 and consistent with the
              "disconnected letters" seen on Windows). We use arabic-reshaper (contextual forms) +
              python-bidi (visual order). Needs a font containing the Arabic Presentation Forms-B
              block; the bundled IBM Plex Sans Arabic does. Verified against a shaping renderer.
* "native"  - only if the start-up probe PROVES the renderer joins letters itself. Text is then
              passed through unchanged. Never observed in development: unverified on any device.

Stored text always stays in logical order; only the string handed to a Kivy label changes.
"""
import re
from typing import Callable, List

_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

_mode = "reshape"
_base_rtl = True          # paragraph direction of the UI language
_reshaper = None


def has_arabic(text: str) -> bool:
    return bool(_ARABIC.search(text or ""))


def set_mode(mode: str) -> None:
    global _mode
    if mode not in ("native", "reshape"):
        raise ValueError(mode)
    _mode = mode


def get_mode() -> str:
    return _mode


def set_base_direction(rtl: bool) -> None:
    global _base_rtl
    _base_rtl = bool(rtl)


def _shape_line(line: str) -> str:
    global _reshaper
    if _reshaper is None:
        import arabic_reshaper
        _reshaper = arabic_reshaper.ArabicReshaper()
    from bidi.algorithm import get_display
    return get_display(_reshaper.reshape(line), base_dir="R" if _base_rtl else "L")


def line_visual(line: str) -> str:
    if not has_arabic(line):
        return line
    if _mode == "reshape":
        return _shape_line(line)
    return line


def visual(text: str) -> str:
    """Logical text -> string to give to a Kivy Label. Handles several lines."""
    return "\n".join(line_visual(line) for line in (text or "").split("\n"))


def wrap_visual(text: str, max_width: float, measure: Callable[[str], float]) -> str:
    """Wrap LOGICAL text into lines no wider than max_width, then convert each line for display."""
    out: List[str] = []
    for paragraph in (text or "").split("\n"):
        line: List[str] = []
        for word in paragraph.split(" "):
            candidate = line + [word]
            if line and measure(line_visual(" ".join(candidate))) > max_width:
                out.append(line_visual(" ".join(line)))
                line = [word]
            else:
                line = candidate
        out.append(line_visual(" ".join(line)))
    return "\n".join(out)
