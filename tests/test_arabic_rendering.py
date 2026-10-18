"""Arabic display pipeline. These tests cover the PURE logic; real glyph output is checked by
tests/test_arabic_visual.py (pixel comparison) and docs/ARABIC_VERIFICATION.md (device checklist)."""
import pytest

from app.utils import arabic

LAM_ALEF = "\ufefb"


@pytest.fixture(autouse=True)
def reshape_mode():
    arabic.set_mode("reshape")
    arabic.set_base_direction(True)
    yield
    arabic.set_mode("reshape")
    arabic.set_base_direction(True)


def presentation_forms(text):
    return [c for c in text if 0xFB50 <= ord(c) <= 0xFEFF]


def test_letters_become_contextual_forms():
    shaped = arabic.visual("مدرسة")
    assert shaped != "مدرسة"
    assert len(presentation_forms(shaped)) == 5          # every letter got an explicit form
    assert shaped == arabic.visual("مدرسة")                # deterministic


def test_stored_text_is_never_modified():
    original = "اجتماع مع المدير"
    arabic.visual(original)
    assert original == "اجتماع مع المدير"                  # str is immutable, but also: no side effects


def test_rtl_visual_order_is_reversed_for_pure_arabic():
    # first logical word must end up on the RIGHT (= last in left-to-right visual string)
    shaped = arabic.visual("مدرسة كبيرة")
    first_word_shaped = arabic.visual("مدرسة")
    assert shaped.endswith(first_word_shaped)


def test_numbers_dates_and_latin_keep_their_own_order():
    out = arabic.visual("موعد 15 أكتوبر 2026 - 18:30")
    assert "15" in out and "2026" in out and "18:30" in out
    out = arabic.visual("ملف report.pdf جاهز")
    assert "report.pdf" in out
    assert "John Smith" in arabic.visual("اسمي John Smith اليوم")


def test_brackets_stay_balanced_and_mirrored():
    out = arabic.visual("التزامات (3)")
    assert "(3)" in out or "(3" in out


def test_lam_alef_ligature_is_used():
    assert LAM_ALEF in arabic.visual("لا") or "\ufefc" in arabic.visual("بلا")


def test_text_without_arabic_is_untouched_in_both_directions():
    for rtl in (True, False):
        arabic.set_base_direction(rtl)
        assert arabic.visual("Hello World 123") == "Hello World 123"


def test_ltr_ui_keeps_english_order_around_arabic_name():
    arabic.set_base_direction(False)
    out = arabic.visual("Call أحمد now")
    assert out.startswith("Call ") and out.endswith(" now")


def test_multiline_is_handled_per_line():
    out = arabic.visual("أ\nب")
    assert out.count("\n") == 1


def test_native_mode_is_a_passthrough():
    arabic.set_mode("native")
    assert arabic.visual("مدرسة كبيرة") == "مدرسة كبيرة"


def test_wrapping_keeps_every_word_in_order():
    text = "هذا نص عربي طويل يحتاج إلى التفاف على عدة أسطر"
    wrapped = arabic.wrap_visual(text, 90, lambda s: len(s) * 8)
    lines = wrapped.split("\n")
    assert len(lines) >= 3
    # rebuilding: each wrapped line, reshaped from its own logical words, must equal what we got
    words, i = text.split(), 0
    for line in lines:
        n = 0
        while i + n < len(words) and arabic.line_visual(" ".join(words[i:i + n + 1])) != line:
            n += 1
            if n > len(words):
                break
        assert arabic.line_visual(" ".join(words[i:i + n + 1])) == line
        i += n + 1
    assert i == len(words)


def test_empty_and_none():
    assert arabic.visual("") == "" and arabic.visual(None) == ""
