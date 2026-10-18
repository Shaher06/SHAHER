from datetime import timedelta

from kivy.uix.boxlayout import BoxLayout

from app.i18n import t
from app.screens.base import BaseScreen
from app.utils import dates
from app.widgets import theme
from app.widgets.cards import TapSurface
from app.widgets.common import ALabel, AButton, Surface, IconButton, rtl_row, spacer, touch
from app.widgets.theme import dp, fs, gap


class WeekScreen(BaseScreen):
    """Seven-day overview. Tap an item to edit it, or '+' on a day to add something to that day."""
    title_key = "week.title"

    def build(self):
        self.start = None

    def refresh(self):
        c = self.app.ctx.commitments
        today = c.now().date()
        if self.start is None:
            self.start = today
        box = self.content
        box.clear_widgets()
        end = self.start + timedelta(days=6)
        nav = rtl_row(IconButton("back", lambda: self._shift(-7), kind="tonal"),
                      ALabel(f"{dates.format_short(self.start)} – {dates.format_short(end)}", halign="center",
                             font_size=fs(15), bold=True, size_hint_y=1),
                      IconButton("chevron", lambda: self._shift(7), kind="tonal"), height=touch(48))
        box.add_widget(nav)
        if self.start != today:
            box.add_widget(AButton(t("week.this_week"), "ghost", on_action=lambda: self._shift(0, reset=True)))
        overdue = c.list("overdue")
        for day, items in c.week_overview(self.start):
            is_today = day == today
            card = Surface(orientation="vertical", padding=gap(12), spacing=gap(6), size_hint_y=None,
                           bg_color=list(theme.ACCENT_SOFT) if is_today else [0, 0, 0, 0])
            card.bind(minimum_height=card.setter("height"))
            head = f"{dates.weekday_name(day)} · {dates.format_short(day)}"
            if is_today:
                head += f" · {t('due.today')}"
            card.add_widget(rtl_row(ALabel(head, font_size=fs(15), bold=True, size_hint_y=1),
                                    ALabel(t("week.count", n=len(items)), shrink=True, font_size=fs(13), color=theme.MUTED,
                                           size_hint_y=1),
                                    IconButton("plus", lambda d=day: self._add_on(d), kind="ghost", size_dp=44),
                                    height=touch(44)))
            if not items:
                card.add_widget(ALabel(t("week.free"), font_size=fs(13.5), color=theme.MUTED))
            for item in items:
                row = TapSurface(orientation="horizontal", padding=[gap(10), gap(6)], size_hint_y=None, height=touch(44),
                                 elevated=False, bg_color=list(theme.FIELD[:3]) + [0.6])
                row.on_release = lambda it=item: self.app.open_commitment_form(it)
                row.add_widget(ALabel(f"{dates.format_time(item.due_at)}  {item.title}", font_size=fs(14), size_hint_y=1,
                                      color=theme.DANGER if item.is_overdue(c.now()) else theme.TEXT))
                card.add_widget(row)
            box.add_widget(card)
        if overdue and self.start <= today:
            box.add_widget(AButton(t("week.overdue_link", n=len(overdue)), "tonal", icon="alert",
                                   on_action=lambda: self.app.show_commitments("overdue")))

    def _shift(self, days, reset=False):
        c = self.app.ctx.commitments
        self.start = c.now().date() if reset else self.start + timedelta(days=days)
        self.refresh()
        self.scroll_top()

    def _add_on(self, day):
        from datetime import datetime
        due = datetime.combine(day, datetime.min.time()).replace(hour=9)
        now = self.app.ctx.commitments.now()
        if due <= now:
            from app.services.quick_add import default_due
            due = default_due(now) if day == now.date() else due
        self.app.open_commitment_form(None, due=due)
