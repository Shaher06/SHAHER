from datetime import timedelta

from kivy.uix.boxlayout import BoxLayout

from app.i18n import t
from app.screens.base import BaseScreen
from app.services.quick_add import default_due
from app.utils.validation import PRIORITY_KEYS, ValidationError
from app.widgets import theme
from app.widgets.common import ALabel, AButton, Chip, FormField, rtl_row, spacer, touch
from app.widgets.dialogs import Choice, confirm
from app.widgets.pickers import DateTimeField, chip_scroller
from app.widgets.theme import dp, fs, gap

OFFSET_MINUTES = [0, 10, 30, 60, 1440]


def offset_options():
    return [(m, t(f"offset.{m}")) for m in OFFSET_MINUTES]


class CommitmentFormScreen(BaseScreen):
    show_back = True
    back_target = "commitments"

    def build(self):
        self.item, self.priority, self.reminder_on, self._saving = None, "medium", False, False
        self.title_field = FormField(t("form.title"), t("form.title_hint"))
        self.desc_field = FormField(t("form.notes"), t("form.notes_hint"), multiline=True)
        self.when = DateTimeField(t("form.due"))
        self.category_field = FormField(t("form.category"), t("form.category_hint"))
        self.cat_holder = BoxLayout(size_hint_y=None, height=0)
        self.priority_chips = {k: Chip(t("prio." + k), on_action=lambda k=k: self.set_priority(k)) for k in PRIORITY_KEYS}
        self.reminder_chip = Chip(t("form.reminder_off"), on_action=self.toggle_reminder, icon="bell")
        self.offset_choice = Choice(t("form.reminder_when"), offset_options(), 30)
        self.reminder_note = ALabel("", font_size=fs(12.5), color=theme.WARNING)
        self.permission_button = AButton(t("perm.allow"), "tonal", on_action=self.ask_permission)
        self.error_label = ALabel("", color=theme.DANGER, font_size=fs(14))
        self.save_button = AButton(t("common.save"), "primary", icon="check", on_action=self.save)
        self.delete_button = AButton(t("common.delete"), "danger", icon="trash", on_action=self.delete)
        c = self.content
        for w in (self.title_field, self.when, self.desc_field, self.category_field):
            c.add_widget(w)
        c.add_widget(self.cat_holder)
        c.add_widget(ALabel(t("form.priority"), font_size=fs(13), color=theme.MUTED))
        c.add_widget(chip_scroller(list(self.priority_chips.values())))
        c.add_widget(ALabel(t("form.reminder"), font_size=fs(13), color=theme.MUTED))
        c.add_widget(rtl_row(self.reminder_chip, self.offset_choice, height=touch(48)))
        c.add_widget(self.reminder_note)
        c.add_widget(self.permission_button)
        c.add_widget(self.error_label)
        c.add_widget(self.save_button)
        self._delete_slot = c

    def load(self, item, due=None):
        self.item, self._saving = item, False
        self.error_label.raw = ""
        ctx = self.app.ctx
        if self._delete_slot and self.delete_button.parent is self._delete_slot:
            self._delete_slot.remove_widget(self.delete_button)
        self.scroll_top()
        if item is None:
            self.set_title(t("form.add_title"))
            self.title_field.text = self.desc_field.text = self.category_field.text = ""
            self.when.set_datetime(due or default_due(ctx.commitments.now()))
            self.priority = ctx.prefs.get("default_priority")
            self.reminder_on = ctx.prefs.flag("reminder_default_on")
            self.offset_choice.set_options(offset_options(), ctx.prefs.int("reminder_offset_minutes", 30))
        else:
            self.set_title(t("form.edit_title"))
            self.title_field.text, self.desc_field.text = item.title, item.description
            self.category_field.text = item.category
            self.when.set_datetime(item.due_at)
            self.priority, self.reminder_on = item.priority, item.reminder_enabled
            minutes = int((item.due_at - item.reminder_at).total_seconds() // 60) if item.reminder_at else None
            self.offset_choice.set_options(offset_options(), minutes if minutes in OFFSET_MINUTES
                                           else ctx.prefs.int("reminder_offset_minutes", 30))
            self._delete_slot.add_widget(self.delete_button)
        cats = ctx.commitments.categories()[:8]
        self.cat_holder.clear_widgets()
        self.cat_holder.height = touch(44) if cats else 0
        if cats:
            self.cat_holder.add_widget(chip_scroller([Chip(c, on_action=lambda c=c: setattr(self.category_field, "text", c))
                                                      for c in cats]))
        self._refresh_controls()

    def _refresh_controls(self):
        for k, chip in self.priority_chips.items():
            chip.active = (k == self.priority)
        self.reminder_chip.raw = t("form.reminder_on") if self.reminder_on else t("form.reminder_off")
        self.reminder_chip.active = self.reminder_on
        self.offset_choice.opacity = 1 if self.reminder_on else 0.4
        self.offset_choice.disabled = not self.reminder_on
        self._refresh_reminder_note()

    def _refresh_reminder_note(self):
        backend = self.app.ctx.backend
        note, show_perm = "", False
        if self.reminder_on:
            if backend.background:
                if backend.notifications_allowed():
                    note = t("form.note_android_ok")
                else:
                    note, show_perm = t("form.note_perm_denied"), True
            else:
                note = t("form.note_desktop")
        self.reminder_note.raw = note
        self.reminder_note.opacity = 1 if note else 0
        self.permission_button.opacity = 1 if show_perm else 0
        self.permission_button.disabled = not show_perm
        self.permission_button.height = touch(48) if show_perm else 0

    def set_priority(self, key):
        self.priority = key
        self._refresh_controls()

    def toggle_reminder(self):
        self.reminder_on = not self.reminder_on
        backend = self.app.ctx.backend
        if self.reminder_on and backend.background and not backend.notifications_allowed():
            backend.request_permission()
        self._refresh_controls()

    def ask_permission(self):
        self.app.ctx.backend.request_permission()
        self.app.toast(t("perm.hint"))

    def save(self):
        if self._saving:                    # ignore repeated taps
            return
        due = self.when.get_datetime()
        if due is None:
            self._show_errors([t("err.datetime_invalid")])
            return
        reminder_at = due - timedelta(minutes=int(self.offset_choice.value)) if self.reminder_on else None
        ctx = self.app.ctx
        self._saving = True
        try:
            args = (self.title_field.text, self.desc_field.text, due, self.priority,
                    self.category_field.text, self.reminder_on, reminder_at)
            if self.item is None:
                ctx.commitments.create(*args)
            else:
                ctx.commitments.update(self.item.id, *args)
            if self.reminder_on:
                ctx.prefs.set("reminder_offset_minutes", self.offset_choice.value)
        except ValidationError as e:
            self._saving = False
            self._show_errors(e.errors)
            return
        except Exception:
            self._saving = False
            self.app.report_unexpected_error(t("msg.save_failed"))
            return
        self.app.toast(t("msg.saved"), "success")
        self.app.go("commitments")

    def delete(self):
        item = self.item
        if item is None:
            return

        def go():
            self.app.ctx.commitments.delete(item.id)
            self.app.toast(t("msg.deleted"))
            self.app.go("commitments")
        confirm(t("delete.title"), t("delete.message", title=item.title), go, yes_text=t("common.delete"), danger=True)

    def _show_errors(self, errors):
        self.error_label.raw = "\n".join(errors)
        self.app.toast(errors[0], "error")
