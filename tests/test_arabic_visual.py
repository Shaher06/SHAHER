"""Pixel-level check: our reshape pipeline drawn by a NON-shaping renderer (PIL basic layout,
behaves like Kivy's text here) must match a proper shaping renderer (PIL + Raqm) drawing the
logical text. Skipped automatically if Pillow lacks Raqm."""
import numpy as np
import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw, ImageFont, features  # noqa: E402

from app import config  # noqa: E402
from app.utils import arabic  # noqa: E402

pytestmark = pytest.mark.skipif(not features.check("raqm"), reason="Pillow built without Raqm")

PURE_ARABIC = ["مدرسة", "متأخرة", "أحمد", "الإنجاز", "كتاب الكاتب", "اجتماع مع المدير",
               "أهلا بيك يا محمد", "التزامات اليوم"]
# Digits / Latin / brackets: Raqm kerns them differently from a basic layout, so pixel diffs cannot
# tell "spacing" from "wrong". Order is covered by unit tests + docs/images/arabic_mixed_check.png.
MIXED = ["عندك 3 مهام اليوم", "موعد 15 أكتوبر 2026", "الساعة 18:30", "ملف report.pdf جاهز",
         "التزامات (3)", "أحمد Ali اليوم"]


def _render(text, engine, direction=None):
    font = ImageFont.truetype(str(config.font_path()), 40, layout_engine=engine)
    img = Image.new("L", (1000, 90), 0)
    kw = {"direction": direction} if direction else {}
    ImageDraw.Draw(img).text((10, 10), text, font=font, fill=255, **kw)
    arr = np.array(img)
    cols = np.where(arr.any(axis=0))[0]
    return arr[:, cols.min():cols.max() + 1]


@pytest.mark.parametrize("text", PURE_ARABIC)
def test_reshape_pipeline_matches_a_real_shaping_renderer(text):
    arabic.set_mode("reshape")
    arabic.set_base_direction(True)
    reference = _render(text, ImageFont.Layout.RAQM, "rtl")
    ours = _render(arabic.visual(text), ImageFont.Layout.BASIC)
    # Raqm applies slightly different spacing around digits/punctuation, so allow 2.5% width drift,
    # then compare the glyph pictures after stretching ours to the reference width.
    drift = abs(reference.shape[1] - ours.shape[1]) / reference.shape[1]
    assert drift <= 0.025, f"overall width differs by {drift:.1%}"
    h = min(reference.shape[0], ours.shape[0])
    ours_fit = np.array(Image.fromarray(ours[:h]).resize((reference.shape[1], h)))
    diff = np.abs(reference[:h].astype(int) - ours_fit.astype(int)).mean()
    assert diff < 12, (f"glyph shapes/order differ (mean pixel diff {diff:.1f})")


@pytest.mark.parametrize("text", MIXED)
def test_mixed_text_has_the_same_overall_width_as_a_real_shaping_renderer(text):
    arabic.set_mode("reshape")
    arabic.set_base_direction(True)
    reference = _render(text, ImageFont.Layout.RAQM, "rtl")
    ours = _render(arabic.visual(text), ImageFont.Layout.BASIC)
    assert abs(reference.shape[1] - ours.shape[1]) / reference.shape[1] <= 0.04


def test_font_covers_every_form_the_reshaper_can_produce():
    import arabic_reshaper
    from fontTools.ttLib import TTFont
    cmap = TTFont(str(config.font_path())).getBestCmap()
    missing = set()
    for ch in (chr(c) for c in range(0x621, 0x64B)):
        for ctx in (ch, "ب" + ch, ch + "ب", "ب" + ch + "ب"):
            for out in arabic_reshaper.reshape(ctx):
                if ord(out) > 0x600 and ord(out) not in cmap and not 0x63B <= ord(out) <= 0x63F:
                    missing.add(hex(ord(out)))
    assert not missing, f"font lacks glyphs: {sorted(missing)}"


@pytest.mark.parametrize("text", ["اجتماع مع المدير", "متأخرة", "أهلا بيك يا محمد"])
def test_the_check_itself_rejects_unprocessed_text(text):
    """Guard against a vacuous test: raw logical text on a non-shaping renderer must FAIL."""
    reference = _render(text, ImageFont.Layout.RAQM, "rtl")
    raw = _render(text, ImageFont.Layout.BASIC)
    h = min(reference.shape[0], raw.shape[0])
    fit = np.array(Image.fromarray(raw[:h]).resize((reference.shape[1], h)))
    assert np.abs(reference[:h].astype(int) - fit.astype(int)).mean() >= 15
