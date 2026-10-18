from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from app import i18n
from app.i18n import t
from app.utils import dates
from app.widgets import theme
from app.widgets.common import ALabel, AButton, IconButton, Surface, rtl_row, spacer, touch
from app.widgets.icons import Icon
from app.widgets.theme import dp, fs, gap


class MeterBar(Widget):
    """Thin progress bar that fills from the START side (right in Arabic, left in English)."""

    def __init__(self, value=0.0, color=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(10))
        super().__init__(**kwargs)
        self.value, self.color = value, color or theme.ACCENT
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        r = self.height / 2
        with self.canvas:
            Color(*theme.ACCENT[:3], 0.18)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r])
            if self.value > 0:
                w = max(self.height, self.width * min(self.value, 1.0))
                Color(*self.color)
                x = self.right - w if i18n.is_rtl() else self.x
                RoundedRectangle(pos=(x, self.y), size=(w, self.height), radius=[r])


class TapSurface(ButtonBehavior, Surface):
    pass


def section_title(text, action_text=None, action=None):
    label = ALabel(text, font_size=fs(18), bold=True, size_hint_y=None)
    if not action:
        return label
    link = AButton(action_text, "ghost", on_action=action, size_hint_x=None, width=dp(110), height=touch(40),
                   font_size=fs(13.5))
    return rtl_row(label, link, height=touch(40))


def small_button(text, kind="secondary", on_action=None, icon=None):
    return AButton(text, kind, on_action=on_action, icon=icon, height=touch(42), font_size=fs(13.5),
                   padding=[gap(8), 0])


class StatCard(TapSurface):
    def __init__(self, label, value, icon, color=None, on_action=None, **kwargs):
        super().__init__(orientation="vertical", padding=gap(12), spacing=gap(2), **kwargs)
        self._action = on_action
        color = color or theme.TEXT
        top = rtl_row(Icon(icon, color=color, size_dp=20), ALabel(str(value), font_size=fs(26), bold=True,
                                                                   color=color, halign=("right" if i18n.is_rtl() else "left")),
                      height=gap(40))
        self.add_widget(top)
        self.add_widget(ALabel(label, font_size=fs(13), color=theme.MUTED))

    def on_release(self):
        if self._action:
            self._action()


class EmptyState(Surface):
    def __init__(self, title, hint="", icon="sparkle", action_text=None, action=None, **kwargs):
        super().__init__(orientation="vertical", padding=gap(22), spacing=gap(8), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        holder = BoxLayout(size_hint_y=None, height=dp(44))
        holder.add_widget(Widget())
        holder.add_widget(Icon(icon, color=theme.ACCENT, size_dp=34))
        holder.add_widget(Widget())
        self.add_widget(holder)
        self.add_widget(ALabel(title, halign="center", font_size=fs(17), bold=True))
        if hint:
            self.add_widget(ALabel(hint, halign="center", font_size=fs(13.5), color=theme.MUTED))
        if action:
            self.add_widget(AButton(action_text, "primary", on_action=action, icon="plus"))


class CommitmentCard(Surface):
    """One commitment. Urgency and state are shown with TEXT + ICON, never colour alone.
    `actions`: name -> callback(commitment). Known names: complete reopen edit reschedule archive
    restore delete focus."""

    def __init__(self, item, now, actions, compact=False, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, **kwargs)
        overdue = item.is_overdue(now)
        stripe_color = theme.DANGER if overdue else theme.PRIORITY_COLORS.get(item.priority, theme.MUTED)
        body = BoxLayout(orientation="vertical", padding=[gap(14), gap(12)], spacing=gap(6), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        body.bind(height=lambda w, h: setattr(self, "height", h))

        is_open = item.status == "open"
        title_row = [ALabel(item.title, font_size=fs(17), bold=True,
                            color=theme.TEXT if is_open else theme.MUTED)]
        if "focus" in actions and is_open:
            starred = item.focus_date == now.date()
            title_row.append(IconButton("star_fill" if starred else "star", lambda: actions["focus"](item),
                                        kind="tonal" if starred else "ghost", size_dp=44))
        body.add_widget(rtl_row(*title_row, height=touch(44)) if len(title_row) > 1 else title_row[0])

        meta = [self._chip("clock", dates.friendly_due(item.due_at, now.date()),
                           theme.DANGER if overdue else theme.MUTED)]
        if overdue:
            meta.append(self._chip("alert", t("card.overdue"), theme.DANGER))
        elif item.status == "completed":
            meta.append(self._chip("check", t("card.completed"), theme.ACCENT_TEXT))
        meta.append(self._chip(None, t("card.priority", p=t("prio." + item.priority)),
                               theme.PRIORITY_COLORS[item.priority]))
        if item.category:
            meta.append(self._chip(None, item.category, theme.ACCENT_TEXT))
        if item.reminder_enabled and is_open:
            meta.append(self._chip("bell", "", theme.WARNING))
        row = rtl_row(*meta, spacing=gap(12), height=dp(24))
        row.add_widget(spacer())
        body.add_widget(row)

        if item.description and not compact:
            text = item.description if len(item.description) < 140 else item.description[:137] + "..."
            body.add_widget(ALabel(text, font_size=fs(13.5), color=theme.MUTED))

        if not compact:
            plan = {"open": [("complete", "primary", "card.complete", "check"), ("reschedule", "secondary", "card.reschedule", None),
                             ("edit", "secondary", "card.edit", None), ("archive", "secondary", "card.archive", None)],
                    "completed": [("reopen", "secondary", "card.reopen", None), ("archive", "secondary", "card.archive", None)],
                    "archived": [("restore", "secondary", "card.restore", None), ("delete", "danger", "card.delete", None)]}[item.status]
            buttons = [small_button(t(k), kind, (lambda n=n: actions[n](item)), icon)
                       for n, kind, k, icon in plan if n in actions]
            if buttons:
                # Four buttons do not fit one row on a narrow screen or with large text: use two rows.
                from kivy.core.window import Window
                crowded = len(buttons) > 2 and (theme.TEXT_SCALE > 1 or Window.width < 400)
                if crowded:
                    half = (len(buttons) + 1) // 2
                    body.add_widget(rtl_row(*buttons[:half], height=touch(42)))
                    body.add_widget(rtl_row(*buttons[half:], height=touch(42)))
                else:
                    body.add_widget(rtl_row(*buttons, height=touch(42)))
        self.add_widget(body)
        stripe = Widget(size_hint_x=None, width=dp(5))
        with stripe.canvas:
            Color(*stripe_color)
            self._stripe = RoundedRectangle(pos=stripe.pos, size=stripe.size, radius=[dp(3)])
        stripe.bind(pos=lambda w, v: setattr(self._stripe, "pos", v), size=lambda w, v: setattr(self._stripe, "size", v))
        if i18n.is_rtl():
            self.add_widget(stripe)                    # right edge
        else:
            self.add_widget(stripe, index=len(self.children))   # left edge

    @staticmethod
    def _chip(icon, text, color):
        parts = []
        if icon:
            parts.append(Icon(icon, color=color, size_dp=15))
        if text:
            parts.append(ALabel(text, shrink=True, font_size=fs(13), color=color))
        box = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(4), height=dp(24))
        for w in (reversed(parts) if i18n.is_rtl() else parts):
            box.add_widget(w)
        box.bind(minimum_width=box.setter("width"))
        box.width = sum(p.width for p in parts) + dp(4) * max(0, len(parts) - 1)
        for p in parts:
            p.bind(width=lambda *_: setattr(box, "width", sum(q.width for q in parts) + dp(4) * max(0, len(parts) - 1)))
        return box


class HabitCard(TapSurface):
    def __init__(self, habit, stats, on_open, on_success, on_setback, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, padding=gap(14), spacing=gap(8), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self._open = on_open
        self.add_widget(ALabel(habit.name, font_size=fs(17), bold=True))
        self.add_widget(MeterBar(stats.progress))
        line = t("habit.streak_line", cur=stats.current_streak, target=stats.target_days)
        if stats.completed:
            line += " — " + t("habit.goal_reached")
        self.add_widget(ALabel(line, font_size=fs(13.5), color=theme.MUTED))
        if habit.status == "active":
            if stats.today_state == "pending":
                self.add_widget(rtl_row(small_button(t("habit.log_success"), "tonal", on_success, "check"),
                                        small_button(t("habit.log_setback"), "secondary", on_setback), height=touch(42)))
            else:
                done = t("habit.state_success") if stats.today_state == "success" else t("habit.state_setback")
                self.add_widget(ALabel(t("habit.today_logged", r=done), font_size=fs(13.5),
                                       color=theme.ACCENT_TEXT if stats.today_state == "success" else theme.WARNING))
        else:
            self.add_widget(ALabel(t("habit.archived_tag"), font_size=fs(13.5), color=theme.WARNING))

    def on_release(self):
        self._open()
