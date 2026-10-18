from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout

from app import i18n
from app.i18n import t
from app.utils import platform_utils
from app.widgets import theme
from app.widgets import common
from app.widgets.common import ALabel, Surface
from app.widgets.icons import Icon
from app.widgets.theme import dp, fs, gap


class NavItem(ButtonBehavior, BoxLayout):
    def __init__(self, name, icon, label, on_select, **kwargs):
        super().__init__(orientation="vertical", padding=[0, gap(6)], spacing=dp(2), **kwargs)
        self.name, self._on_select = name, on_select
        self.icon = Icon(icon, size_dp=22, pos_hint={"center_x": .5})
        self.label = ALabel(label, halign="center", font_size=fs(11.5), size_hint_y=1)
        self.label.unbind(texture_size=self.label._fit)
        row = BoxLayout(size_hint_y=None, height=dp(24))
        from kivy.uix.widget import Widget
        row.add_widget(Widget()); row.add_widget(self.icon); row.add_widget(Widget())
        self.add_widget(row)
        self.add_widget(self.label)
        self.set_active(False)

    def set_active(self, active):
        color = theme.ACCENT_TEXT if active else theme.MUTED
        self.icon.color = list(color)
        self.label.color = color
        self._active = active
        self.canvas.before.clear()
        if active:
            with self.canvas.before:
                Color(*theme.ACCENT_SOFT)
                self._pill = RoundedRectangle(pos=self.pos, size=self.size, radius=[theme.RADIUS])
            self.bind(pos=self._move, size=self._move)

    def _move(self, *_):
        if self._active:
            self._pill.pos, self._pill.size = self.pos, self.size

    def on_release(self):
        if common.HAPTICS["on"]:
            platform_utils.vibrate(10)
        self._on_select(self.name)


class NavBar(Surface):
    ITEMS = [("home", "home", "nav.home"), ("commitments", "list", "nav.commitments"),
             ("week", "calendar", "nav.week"), ("habits", "habits", "nav.habits"), ("settings", "settings", "nav.settings")]

    def __init__(self, on_select, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64), padding=[gap(6), gap(4)],
                         spacing=gap(4), radius=0, elevated=True, bordered=False, **kwargs)
        self.items = {}
        for name, icon, key in (reversed(self.ITEMS) if i18n.is_rtl() else self.ITEMS):
            item = NavItem(name, icon, t(key), on_select)
            self.items[name] = item
            self.add_widget(item)

    def set_active(self, name):
        for n, item in self.items.items():
            item.set_active(n == name)
