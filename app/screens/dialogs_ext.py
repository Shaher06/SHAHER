"""Dialogs shared by several screens."""
from datetime import datetime, timedelta

from app.i18n import t
from app.utils.validation import ValidationError
from app.widgets import theme
from app.widgets.common import ALabel, AButton, rtl_row, touch
from app.widgets.dialogs import Dialog
from app.widgets.pickers import DateTimeField
from app.widgets.theme import dp, fs


class RescheduleDialog(Dialog):
    """Move an open commitment to a realistic new time (quick options or a custom date/time)."""

    def __init__(self, app, item, on_done):
        super().__init__(t("resched.title"))
        self.app, self.item, self.on_done = app, item, on_done
        now = app.ctx.commitments.now()
        self.add_widget(ALabel(item.title, color=theme.MUTED, font_size=fs(14)))
        time_of_day = item.due_at.time()

        def at(day_offset, hour=None):
            base = (now + timedelta(days=day_offset)).date()
            return datetime.combine(base, time_of_day if hour is None else datetime.min.time().replace(hour=hour))

        options = []
        evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if evening > now:
            options.append((t("resched.this_evening"), evening))
        options += [(t("resched.tomorrow"), at(1)), (t("resched.in_two_days"), at(2)),
                    (t("resched.next_week"), at(7))]
        for label, due in options:
            self.add_widget(AButton(label, "secondary", on_action=lambda d=due: self.apply(d)))
        self.custom = DateTimeField(t("resched.custom"))
        self.custom.set_datetime(max(item.due_at, now) + timedelta(days=1))
        self.add_widget(self.custom)
        self.add_widget(rtl_row(AButton(t("resched.apply_custom"), "primary", on_action=self.apply_custom),
                                AButton(t("common.cancel"), "ghost", on_action=self.dismiss), height=touch(48)))

    def apply_custom(self):
        due = self.custom.get_datetime()
        if due is None:
            self.app.toast(t("err.datetime_invalid"), "error")
            return
        self.apply(due)

    def apply(self, due):
        try:
            before = self.item.reminder_enabled
            updated = self.app.ctx.commitments.reschedule(self.item.id, due)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error")
            return
        self.dismiss()
        msg = t("resched.done")
        if before and not updated.reminder_enabled:
            msg += " " + t("resched.reminder_off")
        self.app.toast(msg, "success", seconds=4)
        self.on_done()
