from kivy.uix.boxlayout import BoxLayout

from app.i18n import t
from app.screens.base import BaseScreen
from app.utils import dates
from app.utils.validation import ValidationError
from app.widgets import theme
from app.widgets.cards import EmptyState, HabitCard, MeterBar, TapSurface, section_title, small_button
from app.widgets.common import ALabel, AButton, Chip, FormField, Surface, rtl_row, spacer, touch
from app.widgets.dialogs import Dialog, confirm
from app.widgets.theme import dp, fs, gap


def state_text(state):
    return {"success": (t("habit.state_success"), theme.ACCENT_TEXT), "setback": (t("habit.state_setback"), theme.WARNING),
            "missed": (t("habit.state_missed"), theme.MUTED), "pending": (t("habit.state_pending"), theme.MUTED)}.get(
        state, ("", theme.MUTED))


class DayDialog(Dialog):
    """Record, correct or clear the result of one habit day."""

    def __init__(self, app, habit, day, record, on_done):
        super().__init__(dates.format_date(day))
        self.app, self.habit, self.day, self.record, self.on_done = app, habit, day, record, on_done
        current = {"success": t("habit.logged_success"), "setback": t("habit.logged_setback")}.get(
            record.result if record else "", t("habit.not_logged"))
        self.add_widget(ALabel(current, color=theme.MUTED, font_size=fs(14)))
        self.note = FormField(t("habit.note"), t("habit.note_hint"))
        self.note.text = record.note if record else ""
        self.add_widget(self.note)
        self.add_widget(rtl_row(AButton(t("habit.log_success"), "primary", icon="check", on_action=lambda: self.save("success")),
                                AButton(t("habit.log_setback"), "secondary", on_action=lambda: self.save("setback")),
                                height=touch(48)))
        if record:
            self.add_widget(AButton(t("habit.clear_record"), "ghost", on_action=self.clear))
        self.add_widget(AButton(t("common.close"), "ghost", on_action=self.dismiss))

    def save(self, result):
        svc = self.app.ctx.habits
        try:
            if self.record:
                svc.correct_record(self.habit.id, self.day, result, self.note.text)
            else:
                svc.record_day(self.habit.id, self.day, result, self.note.text)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error")
            return
        self.dismiss()
        self.app.toast(t("habit.msg_success") if result == "success" else t("habit.msg_setback"),
                       "success" if result == "success" else "info")
        self.on_done()

    def clear(self):
        def go():
            self.app.ctx.habits.clear_record(self.habit.id, self.day)
            self.dismiss()
            self.on_done()
        confirm(t("habit.clear_title"), t("habit.clear_message"), go, yes_text=t("common.delete"), danger=True)


class HabitsScreen(BaseScreen):
    title_key = "nav.habits"
    show_back = True
    back_target = "home"

    def build(self):
        self.show_archived = False
        self.add_header_action(AButton(t("habit.add"), "primary", icon="plus", size_hint_x=None, width=dp(112),
                                       height=touch(44), on_action=lambda: self.app.open_habit_form(None)))

    def refresh(self):
        svc = self.app.ctx.habits
        self.content.clear_widgets()
        self.content.add_widget(rtl_row(
            Chip(t("habit.active"), active=not self.show_archived, on_action=lambda: self._set_archived(False)),
            Chip(t("habit.archived"), active=self.show_archived, on_action=lambda: self._set_archived(True)),
            height=touch(40)))
        habits = [h for h in svc.list(include_archived=True) if (h.status == "archived") == self.show_archived]
        if not habits:
            if self.show_archived:
                self.content.add_widget(EmptyState(t("habit.none_archived"), icon="habits"))
            else:
                self.content.add_widget(EmptyState(t("habit.empty"), t("habit.empty_hint"), icon="habits",
                                                   action_text=t("habit.add"), action=lambda: self.app.open_habit_form(None)))
        for h in habits:
            stats = svc.stats(h.id)
            self.content.add_widget(HabitCard(
                h, stats, on_open=lambda h=h: self.app.open_habit(h.id),
                on_success=lambda h=h: self._quick(h, "success"), on_setback=lambda h=h: self._quick(h, "setback")))

    def _set_archived(self, value):
        self.show_archived = value
        self.refresh()

    def _quick(self, habit, result):
        try:
            self.app.ctx.habits.record_day(habit.id, self.app.ctx.habits.today(), result)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error")
            return
        self.app.toast(t("habit.msg_success") if result == "success" else t("habit.msg_setback"),
                       "success" if result == "success" else "info")
        self.refresh()


class HabitDetailScreen(BaseScreen):
    show_back = True
    back_target = "habits"

    def build(self):
        self.habit_id = None

    def load(self, habit_id):
        self.habit_id = habit_id

    def refresh(self):
        if self.habit_id is None:
            return
        svc = self.app.ctx.habits
        habit = svc.get(self.habit_id)
        if habit is None:
            self.app.go("habits")
            return
        stats = svc.stats(habit.id)
        self.set_title(habit.name)
        c = self.content
        c.clear_widgets()
        card = Surface(orientation="vertical", padding=gap(16), spacing=gap(8), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(ALabel(f"{stats.current_streak}", font_size=fs(44), bold=True, color=theme.ACCENT_TEXT, halign="center"))
        card.add_widget(ALabel(t("habit.current_days"), font_size=fs(14), color=theme.MUTED, halign="center"))
        card.add_widget(MeterBar(stats.progress))
        card.add_widget(ALabel(t("habit.target_line", target=stats.target_days, pct=int(stats.progress * 100)),
                               font_size=fs(13.5), color=theme.MUTED))
        if stats.completed:
            when = f" — {dates.format_date(stats.completed_on)}" if stats.completed_on else ""
            card.add_widget(ALabel(t("habit.goal_reached") + when, color=theme.ACCENT_TEXT, font_size=fs(14)))
        card.add_widget(rtl_row(self._stat(t("habit.longest"), stats.longest_streak),
                                self._stat(t("habit.total_success"), stats.total_success),
                                self._stat(t("habit.setbacks"), stats.total_setbacks), height=gap(66)))
        c.add_widget(card)
        if habit.status == "active":
            today = svc.today()
            if svc.get_record(habit.id, today) is None:
                c.add_widget(rtl_row(
                    AButton(t("habit.log_success"), "primary", icon="check", on_action=lambda: self._record_today(habit, "success")),
                    AButton(t("habit.log_setback"), "secondary", on_action=lambda: self._record_today(habit, "setback")),
                    height=touch(48)))
                c.add_widget(ALabel(t("habit.today_note"), font_size=fs(12.5), color=theme.MUTED))
        c.add_widget(rtl_row(
            AButton(t("common.edit"), "secondary", on_action=lambda: self.app.open_habit_form(habit.id)),
            AButton(t("habit.restore") if habit.status == "archived" else t("card.archive"), "secondary",
                    on_action=lambda: self._toggle_archive(habit)), height=touch(48)))
        c.add_widget(section_title(t("habit.history")))
        c.add_widget(ALabel(t("habit.history_hint"), font_size=fs(12.5), color=theme.MUTED))
        for day, state, rec in svc.history(habit.id):
            c.add_widget(self._history_row(habit, day, state, rec))

    def _stat(self, label, value):
        box = BoxLayout(orientation="vertical")
        box.add_widget(ALabel(str(value), font_size=fs(22), bold=True, halign="center"))
        box.add_widget(ALabel(label, font_size=fs(12), color=theme.MUTED, halign="center"))
        return box

    def _history_row(self, habit, day, state, rec):
        text, color = state_text(state)
        row = TapSurface(orientation="vertical", size_hint_y=None, padding=[gap(12), gap(8)], spacing=gap(2), elevated=False)
        row.bind(minimum_height=row.setter("height"))
        row.add_widget(rtl_row(ALabel(dates.format_date(day), font_size=fs(14), size_hint_y=1),
                               ALabel(text, shrink=True, font_size=fs(14), color=color, size_hint_y=1), height=touch(34)))
        if rec and rec.note:
            row.add_widget(ALabel(rec.note, font_size=fs(12.5), color=theme.MUTED))
        if habit.status == "active":
            row.on_release = lambda: DayDialog(self.app, habit, day, rec, self.refresh).open()
        return row

    def _record_today(self, habit, result):
        try:
            self.app.ctx.habits.record_day(habit.id, self.app.ctx.habits.today(), result)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error")
            return
        self.app.toast(t("habit.msg_success") if result == "success" else t("habit.msg_setback"),
                       "success" if result == "success" else "info")
        self.refresh()

    def _toggle_archive(self, habit):
        svc = self.app.ctx.habits
        if habit.status == "archived":
            svc.restore(habit.id)
            self.app.toast(t("habit.msg_restored"))
            self.refresh()
        else:
            def go():
                svc.archive(habit.id)
                self.app.toast(t("habit.msg_archived"))
                self.app.go("habits")
            confirm(t("habit.archive_title"), t("habit.archive_message"), go, yes_text=t("card.archive"))


class HabitFormScreen(BaseScreen):
    show_back = True
    back_target = "habits"

    def build(self):
        self.habit, self.reminder_on = None, False
        self.name_field = FormField(t("habit.name"), t("habit.name_hint"))
        self.target_field = FormField(t("habit.target"), "15")
        self.time_field = FormField(t("habit.reminder_time"), "21:00")
        self.reminder_chip = Chip(t("habit.reminder_off"), on_action=self.toggle, icon="bell")
        self.note = ALabel("", font_size=fs(12.5), color=theme.WARNING)
        self.error_label = ALabel("", color=theme.DANGER, font_size=fs(14))
        self.save_button = AButton(t("common.save"), "primary", icon="check", on_action=self.save)
        for w in (self.name_field, self.target_field, rtl_row(self.reminder_chip, height=touch(40)),
                  self.time_field, self.note, self.error_label, self.save_button):
            self.content.add_widget(w)

    def load(self, habit):
        self.habit = habit
        self.error_label.raw = ""
        self.set_title(t("habit.edit_title") if habit else t("habit.new_title"))
        self.name_field.text = habit.name if habit else ""
        self.target_field.text = str(habit.target_days if habit else 15)
        self.time_field.text = (habit.reminder_time or "21:00") if habit else "21:00"
        self.reminder_on = habit.reminder_enabled if habit else False
        self._chips()

    def _chips(self):
        self.reminder_chip.raw = t("habit.reminder_on") if self.reminder_on else t("habit.reminder_off")
        self.reminder_chip.active = self.reminder_on
        self.time_field.opacity = 1 if self.reminder_on else 0.4
        backend = self.app.ctx.backend
        self.note.raw = "" if (not self.reminder_on or backend.background) else t("form.note_desktop")

    def toggle(self):
        self.reminder_on = not self.reminder_on
        backend = self.app.ctx.backend
        if self.reminder_on and backend.background and not backend.notifications_allowed():
            backend.request_permission()
        self._chips()

    def save(self):
        svc = self.app.ctx.habits
        try:
            args = (self.name_field.text, self.target_field.text, self.reminder_on, self.time_field.text)
            habit = svc.create(*args) if self.habit is None else svc.update(self.habit.id, *args)
        except ValidationError as e:
            self.error_label.raw = "\n".join(e.errors)
            self.app.toast(e.errors[0], "error")
            return
        except Exception:
            self.app.report_unexpected_error(t("msg.save_failed"))
            return
        self.app.toast(t("habit.msg_saved"), "success")
        if self.habit is None:
            self.app.open_habit(habit.id)
        else:
            self.app.go("habit_detail")
