import pytest

pytest.importorskip("kivy")
from app.widgets import theme  # noqa: E402

MODES = ("light", "dark")
ACCENTS = list(theme.ACCENTS)


@pytest.fixture(autouse=True)
def reset_theme():
    yield
    theme.apply()


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("accent", ACCENTS)
def test_every_palette_is_readable(mode, accent):
    theme.apply(mode, accent)
    assert theme.contrast(theme.TEXT, theme.BG) >= 7
    assert theme.contrast(theme.TEXT, theme.SURFACE_SOLID) >= 7
    assert theme.contrast(theme.MUTED, theme.BG) >= 4.5
    assert theme.contrast(theme.MUTED, theme.SURFACE_SOLID) >= 4.5
    assert theme.contrast(theme.ON_ACCENT, theme.ACCENT) >= 4.5       # text on primary buttons
    assert theme.contrast(theme.ACCENT_TEXT, theme.SURFACE_SOLID) >= 4.5   # accent used as small text
    assert theme.contrast(theme.ACCENT, theme.BG) >= 3                 # controls/icons vs background
    assert theme.contrast(theme.DANGER, theme.SURFACE_SOLID) >= 4.5     # overdue text
    assert theme.contrast(theme.WARNING, theme.SURFACE_SOLID) >= 4.5


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("custom", ["#FFFF00", "#000000", "#FFFFFF", "#123456", "#FF00FF", "#00FF00"])
def test_any_custom_colour_is_made_readable(mode, custom):
    theme.apply(mode, "custom", custom)
    assert theme.contrast(theme.ON_ACCENT, theme.ACCENT) >= 4.5
    assert theme.contrast(theme.ACCENT_TEXT, theme.SURFACE_SOLID) >= 4.5


def test_dark_is_a_designed_palette_not_an_inversion():
    theme.apply("light"); light_bg = theme.BG
    theme.apply("dark"); dark_bg = theme.BG
    assert theme.luminance(light_bg) > 0.6 and theme.luminance(dark_bg) < 0.05
    assert dark_bg[2] > dark_bg[0]            # navy-leaning, not pure grey/black


def test_system_mode_follows_the_os_value():
    theme.apply("system", system_mode="dark")
    assert theme.MODE == "dark"
    theme.apply("system", system_mode="light")
    assert theme.MODE == "light"


def test_density_text_scale_and_radius_apply():
    theme.apply(density="compact", text_scale="large", radius="round")
    assert theme.DENSITY < 1 and theme.TEXT_SCALE > 1 and theme.RADIUS > 20
    base = theme.fs(10)
    theme.apply(text_scale="standard")
    assert base > theme.fs(10)


def test_colours_are_always_tuples():
    theme.apply()
    for value in (theme.BG, theme.TEXT, theme.FIELD, theme.BORDER, theme.ACCENT, theme.DANGER):
        assert isinstance(value, tuple)
