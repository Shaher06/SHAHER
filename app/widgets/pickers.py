from datetime import timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

from app.i18n import t
from app.utils import dates
from app.widgets import theme
from app.widgets.common import ALabel, AInput, Chip, rtl_row, touch
from app.widgets.theme import dp, fs, gap


def chip_scroller(chips):
    """Horizontally scrolling row of chips that starts at the correct side."""
    from app import i18n
    inner = rtl_row(*chips, height=touch(40))
    inner.size_hint_x = None
    inner.bind(minimum_width=inner.setter("width"))
    scroll = ScrollView(size_hint_y=None, height=touch(44), do_scroll_y=False, bar_width=0,
                        scroll_x=1 if i18n.is_rtl() else 0)
    scroll.add_widget(inner)
    return scroll


class DateTimeField(BoxLayout):
    """Date + time entry. Kivy has no built-in picker, so: two boxes (Arabic or English digits are
    accepted) plus quick-pick chips for the most common choices."""

    TIME_PRESETS = ["09:00", "12:00", "15:00", "18:00", "21:00"]

    def __init__(self, label="", **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=gap(6), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.add_widget(ALabel(label, font_size=fs(13), color=theme.MUTED))
        self.date_input = AInput("2026-10-15")
        self.time_input = AInput("18:30")
        self.add_widget(rtl_row(self._labeled(t("form.date"), self.date_input),
                                self._labeled(t("form.time"), self.time_input), height=touch(48) + dp(22)))
        self.add_widget(chip_scroller([Chip(t("form.q_today"), on_action=lambda: self._shift_date(0)),
                                       Chip(t("form.q_tomorrow"), on_action=lambda: self._shift_date(1)),
                                       Chip(t("form.q_week"), on_action=lambda: self._shift_date(7))]))
        self.add_widget(chip_scroller([Chip(tm, on_action=(lambda tm=tm: setattr(self.time_input, "text", tm)))
                                       for tm in self.TIME_PRESETS]))

    def _labeled(self, text, widget):
        box = BoxLayout(orientation="vertical", spacing=dp(2))
        box.add_widget(ALabel(text, font_size=fs(12), color=theme.MUTED))
        box.add_widget(widget)
        return box

    def _shift_date(self, days):
        self.date_input.text = (dates.now().date() + timedelta(days=days)).strftime(dates.DATE_FMT)

    def set_datetime(self, dt):
        self.date_input.text = dt.strftime(dates.DATE_FMT)
        self.time_input.text = dt.strftime("%H:%M")

    def get_datetime(self):
        """datetime, or None when the text is not a valid date/time."""
        try:
            return dates.combine(self.date_input.text, self.time_input.text)
        except ValueError:
            return None
