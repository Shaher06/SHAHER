from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from app.i18n import t
from app.widgets import theme
from app.widgets.common import ALabel, AButton, Surface, rtl_row, touch
from app.widgets.theme import dp, fs, gap


class Dialog(ModalView):
    """Glass card dialog. Add content with add_widget(); it grows to fit (max 90% of the window)."""

    def __init__(self, title, **kwargs):
        super().__init__(size_hint=(0.92, None), background="", background_color=(0, 0, 0, 0.55),
                         auto_dismiss=True, **kwargs)
        self.card = Surface(orientation="vertical", padding=gap(18), spacing=gap(12), size_hint_y=None,
                            bg_color=list(theme.SURFACE_SOLID))
        self.card.bind(minimum_height=self.card.setter("height"))
        self.card.bind(height=lambda *_: setattr(self, "height", min(self.card.height, Window.height * 0.92)))
        super().add_widget(self.card)
        self.add_widget(ALabel(title, font_size=fs(19), bold=True))

    def add_widget(self, widget, *args, **kwargs):
        if hasattr(self, "card") and widget is not self.card:
            return self.card.add_widget(widget, *args, **kwargs)
        return super().add_widget(widget, *args, **kwargs)


def confirm(title, message, on_yes, yes_text=None, no_text=None, danger=False):
    dlg = Dialog(title)
    dlg.add_widget(ALabel(message, color=theme.MUTED))

    def yes():
        dlg.dismiss()
        on_yes()
    dlg.add_widget(rtl_row(
        AButton(yes_text or t("common.confirm"), "danger" if danger else "primary", on_action=yes),
        AButton(no_text or t("common.cancel"), "secondary", on_action=dlg.dismiss), height=touch(48)))
    dlg.open()
    return dlg


def choose(title, options, on_select, current=None):
    """options: list of (value, label). Calls on_select(value)."""
    dlg = Dialog(title)
    box = BoxLayout(orientation="vertical", spacing=gap(6), size_hint_y=None)
    box.bind(minimum_height=box.setter("height"))
    for value, label in options:
        box.add_widget(AButton(label, "tonal" if value == current else "secondary",
                               icon="check" if value == current else None,
                               on_action=lambda v=value: (dlg.dismiss(), on_select(v))))
    scroll = ScrollView(size_hint_y=None, height=min(touch(48) * len(options) + gap(6) * len(options), dp(320)),
                        do_scroll_x=False)
    scroll.add_widget(box)
    dlg.add_widget(scroll)
    dlg.open()
    return dlg


class Choice(AButton):
    """Button showing the current choice; tapping opens a list. Works in both directions."""

    def __init__(self, title, options, value=None, on_change=None, prefix="", **kwargs):
        self.title, self.options, self.prefix, self.on_change = title, list(options), prefix, on_change
        self.value = value if value is not None else (self.options[0][0] if self.options else None)
        super().__init__("", "secondary", on_action=self._open, **kwargs)
        self._show()

    def set_options(self, options, value=None):
        self.options = list(options)
        self.value = value if value is not None else (self.options[0][0] if self.options else None)
        self._show()

    def _show(self):
        self.raw = f"{self.prefix}{dict(self.options).get(self.value, '')}"

    def _open(self):
        choose(self.title, self.options, self._picked, self.value)

    def _picked(self, value):
        self.value = value
        self._show()
        if self.on_change:
            self.on_change(value)


_active_toast = {"box": None, "event": None}


def toast(message, kind="info", seconds=2.8):
    """Short message above the navigation bar. kind: info | error | success. Replaces any older toast."""
    old = _active_toast["box"]
    if old is not None and old.parent is not None:
        Window.remove_widget(old)
        if _active_toast["event"]:
            _active_toast["event"].cancel()
    colors = {"info": theme.SURFACE_SOLID, "error": theme.DANGER, "success": theme.ACCENT}
    bg = colors.get(kind, theme.SURFACE_SOLID)
    fg = theme.on_color(bg) if kind != "info" else theme.TEXT
    box = Surface(orientation="horizontal", padding=[gap(14), gap(10)], bg_color=list(bg), size_hint=(None, None))
    width = min(Window.width * 0.92, dp(560))
    label = ALabel(message, size_hint_x=None, width=width - gap(28), font_size=fs(14), color=fg)
    box.add_widget(label)
    box.width = width

    def place(*_):
        box.height = label.height + gap(20)
        box.pos = ((Window.width - box.width) / 2, dp(86))
    label.bind(height=place)
    place()
    Window.add_widget(box)
    _active_toast["box"] = box
    _active_toast["event"] = Clock.schedule_once(
        lambda dt: Window.remove_widget(box) if box.parent else None, seconds)
