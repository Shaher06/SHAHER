from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout

from app.i18n import t
from app.screens.base import BaseScreen
from app.screens.dialogs_ext import RescheduleDialog
from app.utils.validation import PRIORITY_KEYS
from app.widgets import theme
from app.widgets.cards import CommitmentCard, EmptyState
from app.widgets.common import ALabel, AButton, AInput, Chip, rtl_row, touch
from app.widgets.dialogs import Choice, confirm
from app.widgets.pickers import chip_scroller
from app.widgets.theme import dp, fs, gap

VIEWS = ["all", "overdue", "today", "upcoming", "completed", "archived"]


class CommitmentsScreen(BaseScreen):
    title_key = "nav.commitments"

    def build(self):
        self.view, self.priority, self.category = "all", "", ""
        self._refresh_trigger = Clock.create_trigger(lambda dt: self.refresh(), 0.25)
        self.add_header_action(AButton(t("common.add"), "primary", icon="plus", size_hint_x=None, width=dp(104),
                                       height=touch(44), on_action=lambda: self.app.open_commitment_form(None)))
        self.search = AInput(t("list.search_hint"))
        self.search.bind_text(lambda _: self._refresh_trigger())
        self.content.add_widget(self.search)
        self.chips = {v: Chip(t("view." + v), active=(v == self.view), on_action=lambda v=v: self.set_view(v)) for v in VIEWS}
        self.content.add_widget(chip_scroller(list(self.chips.values())))
        sort_opts = [("urgency", t("sort.urgency")), ("date", t("sort.date")), ("priority", t("sort.priority"))]
        self.sort_choice = Choice(t("list.sort"), sort_opts, self.app.ctx.prefs.get("sort"), self._set_sort,
                                  prefix=t("list.sort") + ": ", height=touch(44))
        self.priority_choice = Choice(t("list.priority"), [("", t("common.all"))] + [(k, t("prio." + k)) for k in PRIORITY_KEYS],
                                      "", self._set_priority, prefix=t("list.priority") + ": ", height=touch(44))
        self.category_choice = Choice(t("list.category"), [("", t("common.all"))], "", self._set_category,
                                      prefix=t("list.category") + ": ", height=touch(44))
        self.content.add_widget(rtl_row(self.sort_choice, self.priority_choice, height=touch(44)))
        self.content.add_widget(self.category_choice)
        self.count_label = ALabel("", font_size=fs(13), color=theme.MUTED)
        self.content.add_widget(self.count_label)
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=gap(10))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.content.add_widget(self.list_box)

    def set_view(self, view):
        self.view = view
        self.refresh()

    def _set_sort(self, v):
        self.app.ctx.prefs.set("sort", v)
        self.refresh()

    def _set_priority(self, v):
        self.priority = v
        self.refresh()

    def _set_category(self, v):
        self.category = v
        self.refresh()

    def focus_search(self):
        self.search.focus = True

    def refresh(self):
        ctx = self.app.ctx
        c = ctx.commitments
        cats = [("", t("common.all"))] + [(x, x) for x in c.categories()]
        if self.category not in [v for v, _ in cats]:
            self.category = ""
        self.category_choice.set_options(cats, self.category)
        for v, chip in self.chips.items():
            chip.active = (v == self.view)
        items = c.list(self.view, self.search.text, self.priority, self.category, sort=ctx.prefs.get("sort"))
        now = c.now()
        self.list_box.clear_widgets()
        self.count_label.raw = t("list.count", n=len(items))
        if not items:
            filtered = bool(self.search.text.strip() or self.priority or self.category)
            if filtered:
                self.list_box.add_widget(EmptyState(t("list.no_match"), t("list.no_match_hint"), icon="search"))
            else:
                self.list_box.add_widget(EmptyState(t("empty." + self.view), t("empty." + self.view + "_hint"),
                                                    icon="check" if self.view in ("overdue", "completed") else "list"))
            return
        actions = {"complete": self._complete, "reopen": self._reopen, "archive": self._archive,
                   "restore": self._restore, "delete": self._delete, "edit": self.app.open_commitment_form,
                   "reschedule": lambda item: RescheduleDialog(self.app, item, self.refresh).open(),
                   "focus": self._focus}
        for item in items:
            self.list_box.add_widget(CommitmentCard(item, now, actions))

    def _do(self, fn, message):
        self.app.run_action(fn, message, self.refresh)

    def _complete(self, item):
        self.app.complete_commitment(item, self.refresh)

    def _reopen(self, item):
        self._do(lambda: self.app.ctx.commitments.reopen(item.id), t("msg.reopened"))

    def _archive(self, item):
        self._do(lambda: self.app.ctx.commitments.archive(item.id), t("msg.archived"))

    def _restore(self, item):
        self._do(lambda: self.app.ctx.commitments.restore(item.id), t("msg.restored"))

    def _focus(self, item):
        c = self.app.ctx.commitments
        c.set_focus(item.id, item.focus_date != c.now().date())
        self.refresh()

    def _delete(self, item):
        confirm(t("delete.title"), t("delete.message", title=item.title),
                lambda: self._do(lambda: self.app.ctx.commitments.delete(item.id), t("msg.deleted")),
                yes_text=t("common.delete"), danger=True)
