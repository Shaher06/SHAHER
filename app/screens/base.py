from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from app import i18n
from app.widgets import theme
from app.widgets.common import ALabel, IconButton, rtl_row, spacer
from app.widgets.theme import dp, fs, gap


class BaseScreen(Screen):
    """Header + scrolling body. Subclasses override build() (once) and refresh() (every visit).
    Screens are transparent: the app Backdrop shows through."""
    title_key = ""
    show_back = False
    back_target = "home"

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")
        items = []
        if self.show_back:
            items.append(IconButton("back", self.go_back, kind="tonal"))
        self.title_label = ALabel("", font_size=fs(22), bold=True, size_hint_y=1, valign="middle")
        items.append(self.title_label)
        self.header_box = rtl_row(*items, height=dp(60), padding=[gap(14), gap(8)])
        root.add_widget(self.header_box)
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.scroll = scroll
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=gap(12),
                                 padding=[gap(14), gap(6), gap(14), gap(28)])
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.add_widget(root)
        self.set_title_key()
        self.build()

    def set_title_key(self):
        from app.i18n import t
        if self.title_key:
            self.title_label.raw = t(self.title_key)

    def add_header_action(self, widget):
        """Place an extra control at the END side of the header."""
        self.header_box.add_widget(widget, index=len(self.header_box.children) if i18n.is_rtl() else 0)

    def build(self):
        pass

    def refresh(self):
        pass

    def on_pre_enter(self, *args):
        self.refresh()

    def go_back(self):
        self.app.go(self.back_target)

    def set_title(self, text):
        self.title_label.raw = text

    def scroll_top(self):
        self.scroll.scroll_y = 1
