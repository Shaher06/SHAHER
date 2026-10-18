from datetime import timedelta

from app.i18n import t
from app.screens.base import BaseScreen
from app.screens.dialogs_ext import RescheduleDialog
from app.widgets import theme
from app.widgets.cards import CommitmentCard, EmptyState, MeterBar, section_title
from app.widgets.common import ALabel, AButton, Surface
from app.widgets.dialogs import confirm
from app.widgets.theme import dp, fs, gap

FOCUS_SUGGESTED = 3


class ReviewScreen(BaseScreen):
    """Daily Focus + lightweight review. Optional: nothing here is required and nothing is a 'failure'."""
    title_key = "review.title"
    show_back = True
    back_target = "home"

    def refresh(self):
        ctx = self.app.ctx
        c = ctx.commitments
        now = c.now()
        box = self.content
        box.clear_widgets()
        done, total = c.daily_progress()
        summary = Surface(orientation="vertical", padding=gap(14), spacing=gap(8), size_hint_y=None)
        summary.bind(minimum_height=summary.setter("height"))
        summary.add_widget(ALabel(t("review.summary", done=done, total=total) if total else t("review.nothing"),
                                  font_size=fs(15), bold=True))
        if total:
            summary.add_widget(MeterBar(done / total))
        box.add_widget(summary)

        actions = {"complete": self._complete, "reschedule": lambda it: RescheduleDialog(self.app, it, self.refresh).open(),
                   "edit": self.app.open_commitment_form, "focus": self._focus}
        # 1. Focus
        focus = c.focus_items()
        box.add_widget(section_title(t("review.focus", n=len(focus))))
        box.add_widget(ALabel(t("review.focus_hint", n=FOCUS_SUGGESTED), font_size=fs(13), color=theme.MUTED))
        if focus:
            for item in focus:
                box.add_widget(CommitmentCard(item, now, actions))
        else:
            box.add_widget(EmptyState(t("review.focus_empty"), t("review.focus_empty_hint"), icon="star"))
        # 2. Candidates (not already focus)
        focus_ids = {i.id for i in focus}
        candidates = [i for i in c.list_day(now.date(), include_overdue=True) if i.id not in focus_ids]
        candidates.sort(key=lambda i: ({"high": 0, "medium": 1, "low": 2}[i.priority], i.due_at))
        if candidates:
            box.add_widget(section_title(t("review.pending", n=len(candidates))))
            for item in candidates[:8]:
                box.add_widget(CommitmentCard(item, now, actions))
            box.add_widget(AButton(t("review.move_all"), "tonal", icon="move", on_action=self._move_all))
        # 3. Tomorrow
        tomorrow = c.list_day(now.date() + timedelta(days=1))
        box.add_widget(section_title(t("review.tomorrow", n=len(tomorrow))))
        if tomorrow:
            for item in tomorrow:
                box.add_widget(CommitmentCard(item, now, {"edit": self.app.open_commitment_form}, compact=True))
        else:
            box.add_widget(ALabel(t("review.tomorrow_empty"), font_size=fs(14), color=theme.MUTED))

    def _complete(self, item):
        self.app.complete_commitment(item, self.refresh)

    def _focus(self, item):
        c = self.app.ctx.commitments
        on = item.focus_date != c.now().date()
        c.set_focus(item.id, on)
        if on and len(c.focus_items()) > FOCUS_SUGGESTED:
            self.app.toast(t("review.too_many", n=FOCUS_SUGGESTED))
        self.refresh()

    def _move_all(self):
        c = self.app.ctx.commitments
        now = c.now()
        ids = [i.id for i in c.list_day(now.date(), include_overdue=True)]
        tomorrow = now.date() + timedelta(days=1)

        def go():
            n = c.reschedule_many(ids, tomorrow)
            self.app.toast(t("review.moved", n=n), "success")
            self.refresh()
        confirm(t("review.move_title"), t("review.move_message", n=len(ids)), go, yes_text=t("review.move_yes"))
