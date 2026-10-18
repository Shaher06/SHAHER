from datetime import timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout

from app import i18n
from app.i18n import t
from app.screens.base import BaseScreen
from app.screens.dialogs_ext import RescheduleDialog
from app.services.quick_add import quick_add
from app.utils import dates
from app.utils.validation import ValidationError
from app.widgets import theme
from app.widgets.cards import CommitmentCard, EmptyState, MeterBar, StatCard, TapSurface, section_title
from app.widgets.common import ALabel, AButton, AInput, Surface, rtl_row, spacer, touch
from app.widgets.icons import Icon
from app.widgets.theme import dp, fs, gap


class HomeScreen(BaseScreen):
    """Priority order: greeting -> add -> overdue/today -> progress -> next days -> secondary entries."""

    def refresh(self):
        app, ctx = self.app, self.app.ctx
        c = ctx.commitments
        now = c.now()
        name = ctx.prefs.get("user_name")
        greeting = t(dates.greeting_key(now))
        self.set_title(f"{greeting}{'، ' if i18n.is_rtl() else ', '}{name}" if name else greeting)
        box = self.content
        box.clear_widgets()
        box.add_widget(ALabel(dates.format_date(now.date()), color=theme.MUTED, font_size=fs(14)))

        msg = ctx.encourager.home_message()
        if msg:
            key, params = msg
            banner = Surface(orientation="horizontal", padding=gap(12), spacing=gap(10), size_hint_y=None,
                             bg_color=list(theme.ACCENT_SOFT), elevated=False)
            text = ALabel(t(key, **params), font_size=fs(14))
            banner.add_widget(text) if not i18n.is_rtl() else None
            icon = Icon("sparkle", color=theme.ACCENT_TEXT, size_dp=20)
            for w in ((text, icon) if i18n.is_rtl() else (icon,)):
                if w.parent is None:
                    banner.add_widget(w)
            banner.height = max(touch(48), text.height + gap(24))
            text.bind(height=lambda w, h: setattr(banner, "height", max(touch(48), h + gap(24))))
            box.add_widget(banner)

        counts = c.counts()
        total_open = counts["today"] + counts["overdue"] + counts["upcoming"]
        # ---- add ----
        box.add_widget(AButton(t("home.add"), "primary", icon="plus", on_action=lambda: app.open_commitment_form(None)))
        self.quick = AInput(t("home.quick_hint"), on_enter=self._quick_add)
        quick_btn = AButton(t("home.quick_btn"), "tonal", on_action=self._quick_add, size_hint_x=None, width=dp(104))
        box.add_widget(rtl_row(self.quick, quick_btn, height=touch(48)))

        if total_open == 0 and counts["completed"] == 0:
            box.add_widget(EmptyState(t("home.empty_title"), t("home.empty_hint"), icon="sparkle"))
            self._secondary_entries(box)
            return

        # ---- overdue ----
        actions = {"complete": self._complete, "edit": app.open_commitment_form,
                   "reschedule": lambda item: RescheduleDialog(app, item, self.refresh).open(),
                   "archive": self._archive, "focus": self._focus}
        overdue = c.list("overdue", sort=ctx.prefs.get("sort"))
        if overdue:
            box.add_widget(section_title(t("home.overdue", n=len(overdue)), t("home.review_all"),
                                         lambda: app.go("review")))
            for item in overdue[:3]:
                box.add_widget(CommitmentCard(item, now, actions))
            if len(overdue) > 3:
                box.add_widget(AButton(t("home.more_overdue", n=len(overdue) - 3), "ghost",
                                       on_action=lambda: app.show_commitments("overdue")))
        # ---- today ----
        today = c.list("today", sort=ctx.prefs.get("sort"))
        box.add_widget(section_title(t("home.today", n=len(today)), t("home.daily_focus"), lambda: app.go("review")))
        if today:
            for item in today:
                box.add_widget(CommitmentCard(item, now, actions))
        else:
            box.add_widget(EmptyState(t("home.today_empty"), t("home.today_empty_hint"), icon="check"))

        # ---- progress ----
        done, total = c.daily_progress()
        if total > 0:
            card = Surface(orientation="vertical", padding=gap(14), spacing=gap(8), size_hint_y=None)
            card.bind(minimum_height=card.setter("height"))
            card.add_widget(ALabel(t("home.progress", done=done, total=total), font_size=fs(15), bold=True))
            card.add_widget(MeterBar(done / total))
            box.add_widget(card)

        # ---- stats ----
        grid = GridLayout(cols=2, spacing=gap(10), size_hint_y=None, height=gap(2 * 84 + 10))
        stat = lambda label, n, icon, view, color=None: StatCard(label, n, icon, color,
                                                                  on_action=lambda: app.show_commitments(view))
        grid.add_widget(stat(t("stat.upcoming"), counts["upcoming"], "calendar", "upcoming"))
        grid.add_widget(stat(t("stat.completed"), counts["completed"], "check", "completed"))
        box.add_widget(grid)
        grid.height = gap(84)

        # ---- next days ----
        upcoming = c.list("upcoming", sort="date", limit=4)
        if upcoming:
            box.add_widget(section_title(t("home.next_days"), t("home.open_week"), lambda: app.go("week")))
            for item in upcoming:
                box.add_widget(CommitmentCard(item, now, {"edit": app.open_commitment_form}, compact=True))
        self._secondary_entries(box)

    def _secondary_entries(self, box):
        app, ctx = self.app, self.app.ctx
        habits = ctx.habits.list()
        logged = sum(1 for h in habits if ctx.habits.stats(h.id).today_state != "pending")
        line = t("home.habits_line", logged=logged, total=len(habits)) if habits else t("home.habits_none")
        row = TapSurface(orientation="horizontal", padding=gap(14), spacing=gap(12), size_hint_y=None,
                         height=touch(56), elevated=False)
        row.on_release = lambda: app.go("habits")
        parts = [Icon("habits", color=theme.ACCENT_TEXT, size_dp=22), ALabel(f"{t('nav.habits')} — {line}", font_size=fs(14)),
                 Icon("chevron", color=theme.MUTED, size_dp=16)]
        for w in (reversed(parts) if i18n.is_rtl() else parts):
            row.add_widget(w)
        box.add_widget(row)

    # ---- actions ----
    def _quick_add(self):
        title = self.quick.text
        if not title.strip():
            self.quick.focus = True
            return
        try:
            item = quick_add(self.app.ctx.commitments, self.app.ctx.prefs, title)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error")
            return
        self.app.toast(t("home.quick_done", when=dates.friendly_due(item.due_at, self.app.ctx.commitments.now().date())),
                       "success")
        self.refresh()

    def _complete(self, item):
        self.app.complete_commitment(item, self.refresh)

    def _archive(self, item):
        self.app.run_action(lambda: self.app.ctx.commitments.archive(item.id), t("msg.archived"), self.refresh)

    def _focus(self, item):
        c = self.app.ctx.commitments
        on = item.focus_date != c.now().date()
        c.set_focus(item.id, on)
        self.refresh()
