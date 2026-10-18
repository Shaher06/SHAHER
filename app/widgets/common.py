"""Reusable RTL/LTR-aware building blocks. Display text goes through app.utils.arabic.visual()
at the very last moment; nothing stored or edited is ever transformed."""
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.core.image import Texture
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from app import i18n
from app.utils import platform_utils
from app.utils.arabic import has_arabic, line_visual, visual, wrap_visual
from app.widgets import theme
from app.widgets.icons import Icon
from app.widgets.theme import dp, fs, gap

HAPTICS = {"on": False}           # set by the app from the preference
REDUCED_MOTION = {"on": False}
_measure_cache = {}


def start_align() -> str:
    return "right" if i18n.is_rtl() else "left"


def touch(h) -> float:
    """Height that never drops under the 44dp touch-target minimum."""
    return max(dp(44), gap(h))


def display(text: str) -> str:
    return visual(i18n.localize_digits(text or ""))


def _measurer(font_name, font_size):
    key = (font_name, round(font_size, 1))
    if key not in _measure_cache:
        _measure_cache[key] = CoreLabel(font_name=font_name, font_size=font_size)
    core = _measure_cache[key]
    return lambda text: core.get_extents(text)[0]


def rtl_row(*widgets, **kwargs) -> BoxLayout:
    """Horizontal row: the FIRST argument sits at the START side (right in Arabic, left in English)."""
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("spacing", gap(8))
    row = BoxLayout(orientation="horizontal", **kwargs)
    for w in (reversed(widgets) if i18n.is_rtl() else widgets):
        row.add_widget(w)
    if row.size_hint_y is None and "height" not in kwargs:
        row.height = dp(40)
    return row


def spacer():
    return Widget()


class Surface(BoxLayout):
    """Glass-style card: soft shadow, translucent fill, hairline border, rounded corners."""
    bg_color = ListProperty([0, 0, 0, 0])      # transparent => use theme surface
    radius = NumericProperty(0)                # 0 => theme radius
    elevated = BooleanProperty(True)
    bordered = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._instr = []
        self.bind(pos=self._redraw, size=self._redraw, bg_color=self._redraw, radius=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        canvas = self.canvas.before
        canvas.clear()
        r = self.radius or theme.RADIUS
        fill = tuple(self.bg_color) if self.bg_color[3] > 0 else tuple(theme.SURFACE)
        with canvas:
            if self.elevated and self.width > 4:
                for off, alpha in ((dp(3), 0.55), (dp(1.5), 0.9)):
                    Color(theme.SHADOW[0], theme.SHADOW[1], theme.SHADOW[2], theme.SHADOW[3] * alpha)
                    RoundedRectangle(pos=(self.x, self.y - off), size=self.size, radius=[r])
            Color(*fill)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r])
            if self.bordered:
                Color(*theme.BORDER[:3], 0.9)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r), width=1)


class ALabel(Label):
    """Label that takes LOGICAL text via `raw`. shrink=True makes it as wide as its text."""
    raw = StringProperty("")

    def __init__(self, text="", shrink=False, bold=False, **kwargs):
        kwargs.setdefault("halign", start_align())
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("color", theme.TEXT)
        kwargs.setdefault("font_size", fs(15))
        kwargs.setdefault("size_hint_y", None)
        kwargs["font_name"] = theme.FONT_BOLD if bold else theme.FONT
        self._shrink = shrink
        if shrink:
            kwargs.setdefault("size_hint_x", None)
        super().__init__(**kwargs)
        self.raw = text
        self.bind(raw=self._refresh, width=self._refresh, font_size=self._refresh, texture_size=self._fit)
        self._refresh()

    def _refresh(self, *_):
        logical = i18n.localize_digits(self.raw)
        if self._shrink:
            self.text_size = (None, None)
            self.text = visual(logical)
            return
        width = max(self.width, 1)
        self.text_size = (width, None)
        if width > 40:
            self.text = wrap_visual(logical, width * 0.97, _measurer(self.font_name, self.font_size))
        else:
            self.text = visual(logical)

    def _fit(self, *_):
        if self.size_hint_y is None:
            self.height = max(self.texture_size[1], self.font_size * 1.35)
        if self._shrink:
            self.width = self.texture_size[0]


class AButton(ButtonBehavior, Surface):
    """kind: primary | secondary | tonal | danger | ghost. Optional vector icon."""
    raw = StringProperty("")
    kind = StringProperty("secondary")
    pressed = BooleanProperty(False)

    def __init__(self, text="", kind="secondary", on_action=None, icon=None, font_size=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", touch(48))
        kwargs.setdefault("padding", [gap(12), 0])
        kwargs.setdefault("spacing", gap(8))
        super().__init__(**kwargs)
        self.kind = kind
        self.elevated = kind in ("primary", "danger")
        self.bordered = kind in ("secondary", "tonal")
        self._icon = Icon(icon, size_dp=20) if icon else None
        self._label = ALabel(text, halign="center", size_hint=(1, 1), font_size=font_size or fs(15), bold=kind == "primary")
        self._label.size_hint_y = 1
        self._label.unbind(texture_size=self._label._fit)
        parts = [w for w in (self._icon, self._label) if w is not None]
        if not text and self._icon:
            parts = [Widget(), self._icon, Widget()]
        for w in (reversed(parts) if i18n.is_rtl() else parts):
            self.add_widget(w)
        self.raw = text
        self._action = on_action
        self.bind(raw=lambda *_: setattr(self._label, "raw", self.raw), kind=self._restyle, pressed=self._restyle,
                  disabled=self._restyle)
        self._restyle()

    def _restyle(self, *_):
        styles = {
            "primary": (theme.ACCENT, theme.ON_ACCENT),
            "secondary": (theme.FIELD[:3] + (0.9,), theme.TEXT),
            "tonal": (theme.ACCENT_SOFT, theme.ACCENT_TEXT),
            "danger": (theme.DANGER, theme.on_color(theme.DANGER)),
            "ghost": ((0, 0, 0, 0.004), theme.ACCENT_TEXT),   # ~transparent, but not the glass fallback
        }
        bg, fg = styles.get(self.kind, styles["secondary"])
        if self.pressed:
            bg = tuple(min(1, c + 0.1) for c in bg[:3]) + (max(bg[3], 0.22),)
        if self.disabled:
            bg, fg = bg[:3] + (bg[3] * 0.45,), fg[:3] + (0.5,)
        self.bg_color = bg
        self._label.color = fg
        if self._icon:
            self._icon.color = list(fg)

    def on_press(self):
        self.pressed = True

    def on_release(self):
        self.pressed = False
        if HAPTICS["on"]:
            platform_utils.vibrate(12)
        if self._action:
            self._action()

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self.pressed = False
        return super().on_touch_up(touch)


class Chip(AButton):
    """Pill that can be switched on (filters, quick values). Always keeps a text label."""
    active = BooleanProperty(False)

    def __init__(self, text="", active=False, on_action=None, icon=None, **kwargs):
        kwargs.setdefault("height", touch(40))
        kwargs.setdefault("size_hint_x", None)
        kwargs.setdefault("padding", [gap(14), 0])
        super().__init__(text, "secondary", on_action, icon=icon, font_size=fs(13.5), **kwargs)
        self.radius = self.height / 2
        self.active = active
        self.bind(active=self._restyle, raw=self._fit_width)
        self._label.size_hint_x = None
        self._label._shrink = True
        self._label.halign = "center"
        self._label._refresh()
        self._label.bind(width=self._fit_width)
        self._fit_width()
        self._restyle()

    def _fit_width(self, *_):
        extra = (self._icon.width + self.spacing) if self._icon else 0
        self.width = self._label.width + extra + gap(28)

    def _restyle(self, *_):
        super()._restyle()
        if self.active:
            self.bg_color = theme.ACCENT
            self._label.color = theme.ON_ACCENT
            if self._icon:
                self._icon.color = list(theme.ON_ACCENT)


class IconButton(ButtonBehavior, Surface):
    """Round icon-only button (>= 44dp)."""

    def __init__(self, icon, on_action=None, kind="ghost", size_dp=44, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(size_dp), dp(size_dp)))
        super().__init__(**kwargs)
        self.elevated, self.bordered = False, False
        self.radius = dp(size_dp) / 2
        self.kind, self._action = kind, on_action
        self.icon = Icon(icon, size_dp=22, pos_hint={"center_x": .5, "center_y": .5})
        self.padding = [(dp(size_dp) - dp(22)) / 2] * 2
        self.add_widget(self.icon)
        self._style(False)

    def set_icon(self, name):
        self.icon.name = name

    def _style(self, pressed):
        self.bg_color = theme.ACCENT_SOFT if (pressed or self.kind == "tonal") else (0, 0, 0, 0.004)
        self.icon.color = list(theme.ACCENT_TEXT if self.kind != "plain" else theme.TEXT)

    def on_press(self):
        self._style(True)

    def on_release(self):
        self._style(False)
        if HAPTICS["on"]:
            platform_utils.vibrate(12)
        if self._action:
            self._action()


class AInput(FloatLayout):
    """Text field that is safe for Arabic.

    A real Kivy TextInput holds the true (logical) text and handles the keyboard. When the text
    contains Arabic we hide the TextInput's own glyphs and draw a correctly shaped overlay label
    instead; the caret is kept at the end of the text in that mode (Arabic mid-text editing is
    not supported - use the clear button). Latin-only text uses the TextInput directly, so
    English editing is completely normal.
    """

    def __init__(self, hint="", multiline=False, min_height=None, on_enter=None, input_filter=None, **kwargs):
        self.multiline = multiline
        self._pad = (gap(12), gap(10))
        self._min_h = min_height or (touch(48) if not multiline else dp(96))
        kwargs.setdefault("size_hint_y", None)
        kwargs["height"] = self._min_h
        super().__init__(**kwargs)
        self.hint, self._overlay_on, self._blink_on, self._on_enter = hint, False, True, on_enter
        self.ti = TextInput(
            multiline=multiline, font_name=theme.FONT, font_size=fs(16), background_normal="",
            background_active="", background_color=(0, 0, 0, 0), foreground_color=theme.TEXT,
            cursor_color=theme.ACCENT, hint_text="", padding=[self._pad[0], self._pad[1], self._pad[0], self._pad[1]],
            halign=start_align(), write_tab=False, use_bubble=False, use_handles=False,
            input_filter=input_filter, size_hint=(1, 1), pos_hint={"x": 0, "y": 0}, selection_color=(*theme.ACCENT[:3], 0.3))
        self.add_widget(self.ti)
        self.overlay = ALabel("", font_size=fs(16), valign="top" if multiline else "middle", size_hint=(None, None))
        self.overlay.unbind(texture_size=self.overlay._fit)
        self.overlay.bind(texture_size=self._on_overlay_size)
        self.add_widget(self.overlay)
        self.clear_btn = IconButton("close", self._clear, size_dp=36)
        self.add_widget(self.clear_btn)
        self.clear_btn.opacity = 0
        self.clear_btn.disabled = True
        with self.canvas.before:
            self._bg_color = Color(*theme.FIELD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[theme.RADIUS * 0.8])
            self._border_color = Color(*theme.BORDER)
            self._border = Line(rounded_rectangle=(0, 0, 1, 1, 8), width=1)
        with self.canvas.after:
            self._cursor_color = Color(0, 0, 0, 0)
            self._cursor = Rectangle(pos=(0, 0), size=(dp(1.6), dp(20)))
        self.bind(pos=self._layout, size=self._layout)
        self.ti.bind(text=self._on_text, focus=self._on_focus, cursor=self._keep_cursor_at_end)
        self.ti.bind(on_text_validate=lambda *_: self._on_enter and self._on_enter())
        self._blink = Clock.schedule_interval(self._toggle_blink, 0.55)
        self._on_text()

    def on_parent(self, widget, parent):
        if parent is None and getattr(self, "_blink", None):
            self._blink.cancel()

    # ---- text API ----
    @property
    def text(self):
        return self.ti.text

    @text.setter
    def text(self, value):
        self.ti.text = value or ""

    @property
    def focus(self):
        return self.ti.focus

    @focus.setter
    def focus(self, value):
        self.ti.focus = value

    def bind_text(self, callback):
        self.ti.bind(text=lambda *_: callback(self.ti.text))

    def _clear(self):
        self.ti.text = ""
        self.ti.focus = True

    # ---- drawing ----
    def _layout(self, *_):
        r = theme.RADIUS * 0.8
        self._bg.pos, self._bg.size, self._bg.radius = self.pos, self.size, [r]
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, r)
        self._place_overlay()

    def _place_overlay(self):
        end_pad = gap(40) if (self._overlay_on and not self.multiline) else self._pad[0]
        left_pad, right_pad = (end_pad, self._pad[0]) if i18n.is_rtl() else (self._pad[0], end_pad)
        self.overlay.width = max(self.width - left_pad - right_pad, 10)
        self._overlay_pads = (left_pad, right_pad)
        self._refresh_overlay()
        if self.multiline:
            need = max(self._min_h, self.overlay.texture_size[1] + 2 * self._pad[1])
            if abs(need - self.height) > 1:
                self.height = need
                return
        self.overlay.height = self.height - 2 * (self._pad[1] if self.multiline else 0)
        self.overlay.pos = (self.x + left_pad, self.y + (self._pad[1] if self.multiline else 0))
        self.clear_btn.pos = (self.x + gap(4), self.y + (self.height - self.clear_btn.height) / 2) if i18n.is_rtl() \
            else (self.right - self.clear_btn.width - gap(4), self.y + (self.height - self.clear_btn.height) / 2)
        self._place_cursor()

    def _on_overlay_size(self, *_):
        if self.multiline:
            self._place_overlay()

    def _refresh_overlay(self):
        text = self.ti.text
        if not text:
            self.overlay.color = theme.MUTED
            hint = self.hint
            if not self.multiline:                 # one line only: shorten the hint with an ellipsis
                measure = _measurer(self.overlay.font_name, self.overlay.font_size)
                words = hint.split(" ")
                while len(words) > 1 and measure(line_visual(" ".join(words) + "…")) > self.overlay.width * 0.97:
                    words.pop()
                hint = " ".join(words) + ("…" if len(words) < len(hint.split(" ")) else "")
            self.overlay.raw = hint
            self.overlay.opacity = 1
            self.overlay.halign = start_align()
            return
        self.overlay.color = theme.TEXT
        self.overlay.opacity = 1 if self._overlay_on else 0
        self.overlay.halign = "right" if i18n.is_rtl() else "left"
        shown = text
        if not self.multiline and self._overlay_on:     # single line: keep the END visible
            measure = _measurer(self.overlay.font_name, self.overlay.font_size)
            while len(shown) > 1 and measure(line_visual(shown)) > self.overlay.width * 0.97:
                shown = shown[1:]
        self.overlay.raw = shown

    def _on_text(self, *_):
        text = self.ti.text
        self._overlay_on = has_arabic(text)
        self.ti.foreground_color = (0, 0, 0, 0) if self._overlay_on else theme.TEXT
        self.ti.cursor_color = (0, 0, 0, 0) if self._overlay_on else theme.ACCENT
        self.ti.selection_color = (0, 0, 0, 0) if self._overlay_on else (*theme.ACCENT[:3], 0.3)
        show_clear = bool(text) and self._overlay_on and not self.multiline
        self.clear_btn.opacity, self.clear_btn.disabled = (1 if show_clear else 0), not show_clear
        self._place_overlay()

    def _on_focus(self, _w, focused):
        self._border_color.rgba = theme.ACCENT if focused else theme.BORDER
        if focused and self._overlay_on:
            self._keep_cursor_at_end()
        self._place_cursor()

    def _keep_cursor_at_end(self, *_):
        if not self._overlay_on:
            return
        end = self.ti.get_cursor_from_index(len(self.ti.text))
        if tuple(self.ti.cursor) != tuple(end):
            Clock.schedule_once(lambda dt: setattr(self.ti, "cursor", end), 0)

    def _toggle_blink(self, dt):
        self._blink_on = True if REDUCED_MOTION["on"] else not self._blink_on
        self._place_cursor()

    def _place_cursor(self):
        if not (self._overlay_on and self.ti.focus and self._blink_on and self.ti.text):
            self._cursor_color.rgba = (0, 0, 0, 0)
            return
        self._cursor_color.rgba = theme.ACCENT
        line_h = self.overlay.font_size * 1.35
        lines = max(1, self.overlay.text.count("\n") + 1)
        last = self.overlay.text.split("\n")[-1]
        width = _measurer(self.overlay.font_name, self.overlay.font_size)(last)
        left_pad, right_pad = self._overlay_pads
        if i18n.is_rtl():
            x = self.right - right_pad - width - dp(2)
        else:
            x = self.x + left_pad + width + dp(1)
        if self.multiline:
            y = self.top - self._pad[1] - lines * line_h + (line_h - line_h * 0.8) / 2
        else:
            y = self.y + (self.height - line_h * 0.8) / 2
        self._cursor.pos = (x, y)
        self._cursor.size = (dp(1.6), line_h * 0.8)


class FormField(BoxLayout):
    """Caption + AInput."""

    def __init__(self, label, hint="", multiline=False, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=gap(4), **kwargs)
        self.caption = ALabel(label, font_size=fs(13), color=theme.MUTED)
        self.add_widget(self.caption)
        self.input = AInput(hint, multiline=multiline)
        self.add_widget(self.input)
        self.bind(minimum_height=self.setter("height"))

    @property
    def text(self):
        return self.input.text

    @text.setter
    def text(self, value):
        self.input.text = value or ""


class Backdrop(Widget):
    """App background: vertical gradient + two faint accent glows (switchable)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *_):
        self.canvas.clear()
        tex = Texture.create(size=(1, 2), colorfmt="rgba")
        top, bottom = (theme.BG, theme.BG2) if theme.DECOR else (theme.BG, theme.BG)
        buf = bytes(int(c * 255) for c in (*bottom[:3], 1.0)) + bytes(int(c * 255) for c in (*top[:3], 1.0))
        tex.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = "linear"
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=self.pos, size=self.size)
            if theme.DECOR:
                Color(*theme.ACCENT[:3], 0.07)
                Ellipse(pos=(self.right - self.width * 0.55, self.top - self.width * 0.5), size=(self.width * 0.9,) * 2)
                Color(*theme.ACCENT[:3], 0.05)
                Ellipse(pos=(self.x - self.width * 0.5, self.y - self.width * 0.15), size=(self.width * 0.9,) * 2)
