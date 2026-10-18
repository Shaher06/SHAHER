from kivy.graphics import Color, Ellipse, Line
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from app import __version__, config, i18n
from app.i18n import t
from app.screens.base import BaseScreen
from app.services import backup_service, data_service
from app.services.demo_data import add_demo_data, remove_demo_data
from app.services.preferences import _valid_hex
from app.utils import platform_utils
from app.utils.validation import ValidationError
from app.widgets import textengine, theme
from app.widgets.cards import section_title
from app.widgets.common import ALabel, AButton, AInput, Chip, Surface, rtl_row, spacer, touch
from app.widgets.dialogs import Choice, choose, confirm
from app.widgets.icons import Icon
from app.widgets.pickers import chip_scroller
from app.widgets.theme import dp, fs, gap

OFFSETS = [(0, "offset.0"), (10, "offset.10"), (30, "offset.30"), (60, "offset.60"), (1440, "offset.1440")]


class Swatch(ButtonBehavior, Widget):
    """Round accent-colour button; a ring + check mark shows the selected one (not colour alone)."""

    def __init__(self, color, selected, on_action, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(44), dp(44)), **kwargs)
        self._action = on_action
        with self.canvas:
            Color(*color)
            self._dot = Ellipse(pos=(self.x + dp(4), self.y + dp(4)), size=(dp(36), dp(36)))
            if selected:
                Color(*theme.TEXT)
                self._ring = Line(circle=(self.center_x, self.center_y, dp(21)), width=dp(2))
        self.bind(pos=self._move, size=self._move)
        self._selected, self._on_color = selected, theme.on_color(color)
        if selected:
            self.icon = Icon("check", color=self._on_color, size_dp=18)
            self.add_widget(self.icon)
        self._move()

    def _move(self, *_):
        self._dot.pos = (self.x + dp(4), self.y + dp(4))
        if self._selected:
            self._ring.circle = (self.center_x, self.center_y, dp(21))
            self.icon.center = self.center

    def on_release(self):
        self._action()


class SettingsScreen(BaseScreen):
    title_key = "nav.settings"

    # ---------- small builders ----------
    def card(self, title):
        card = Surface(orientation="vertical", padding=gap(14), spacing=gap(10), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(ALabel(title, font_size=fs(17), bold=True))
        self.content.add_widget(card)
        return card

    def label(self, card, text, muted=True, size=14):
        card.add_widget(ALabel(text, font_size=fs(size), color=theme.MUTED if muted else theme.TEXT))

    def chips(self, card, caption, options, current, on_pick):
        card.add_widget(ALabel(caption, font_size=fs(13), color=theme.MUTED))
        card.add_widget(chip_scroller([Chip(label, active=(val == current), on_action=lambda v=val: on_pick(v))
                                       for val, label in options]))

    def toggle(self, card, caption, pref, on_label, off_label, enabled=True):
        on = self.app.ctx.prefs.flag(pref)
        chip = Chip(on_label if on else off_label, active=on, on_action=lambda: self.pick(pref, "0" if on else "1", rebuild=False))
        chip.disabled = not enabled
        card.add_widget(ALabel(caption, font_size=fs(13), color=theme.MUTED))
        card.add_widget(rtl_row(chip, height=touch(40)))

    def pick(self, pref, value, rebuild=True):
        self.app.set_preference(pref, value, rebuild_to="settings" if rebuild else None)
        if not rebuild:
            self.refresh()

    # ---------- screen ----------
    def refresh(self):
        ctx, app, prefs = self.app.ctx, self.app, self.app.ctx.prefs
        self.content.clear_widgets()

        # ===== Personalization =====
        c = self.card(t("set.personal"))
        c.add_widget(ALabel(t("set.name"), font_size=fs(13), color=theme.MUTED))
        self.name_input = AInput(t("set.name_hint"))
        self.name_input.text = prefs.get("user_name")
        c.add_widget(rtl_row(self.name_input, AButton(t("common.save"), "tonal", on_action=self.save_name, size_hint_x=None,
                                                      width=dp(96)), height=touch(48)))
        self.chips(c, t("set.language"), list(i18n.LANGUAGES.items()), prefs.get("language"), lambda v: self.pick("language", v))
        self.chips(c, t("set.theme"), [("light", t("theme.light")), ("dark", t("theme.dark")), ("system", t("theme.system"))],
                   prefs.get("theme_mode"), lambda v: self.pick("theme_mode", v))
        c.add_widget(ALabel(t("set.accent"), font_size=fs(13), color=theme.MUTED))
        current = prefs.get("accent")
        swatches = BoxLayout(size_hint_y=None, height=dp(48), spacing=gap(6))
        names = list(theme.ACCENTS)
        for name in (names if not i18n.is_rtl() else reversed(names)):
            light, dark = theme.ACCENTS[name]
            color = theme.ensure_contrast(theme.hx(dark if theme.MODE == "dark" else light), theme.BG, 3.0)
            swatches.add_widget(Swatch(color, current == name, lambda n=name: self.pick("accent", n)))
        swatches.add_widget(Widget())
        c.add_widget(swatches)
        self.custom_hex = AInput("#RRGGBB")
        self.custom_hex.text = prefs.get("custom_accent")
        c.add_widget(rtl_row(self.custom_hex, AButton(t("set.custom_apply"), "tonal", on_action=self.apply_custom_color,
                                                      size_hint_x=None, width=dp(132)), height=touch(48)))
        self.label(c, t("set.accent_note"), size=12.5)

        a = self.card(t("set.appearance"))
        self.chips(a, t("set.density"), [("comfortable", t("density.comfortable")), ("compact", t("density.compact"))],
                   prefs.get("density"), lambda v: self.pick("density", v))
        self.chips(a, t("set.text_size"), [("standard", t("text.standard")), ("large", t("text.large"))],
                   prefs.get("text_scale"), lambda v: self.pick("text_scale", v))
        self.chips(a, t("set.corners"), [("sharp", t("radius.sharp")), ("soft", t("radius.soft")), ("round", t("radius.round"))],
                   prefs.get("radius"), lambda v: self.pick("radius", v))
        self.toggle(a, t("set.decor"), "decor", t("common.on"), t("common.off"))
        if i18n.language() == "ar":
            self.chips(a, t("set.digits"), [("western", "1 2 3"), ("arabic", "١ ٢ ٣")], prefs.get("digits"),
                       lambda v: self.pick("digits", v))

        # ===== Commitments & reminders =====
        r = self.card(t("set.reminders"))
        r.add_widget(ALabel(t("set.default_offset"), font_size=fs(13), color=theme.MUTED))
        r.add_widget(Choice(t("set.default_offset"), [(m, t(k)) for m, k in OFFSETS], prefs.int("reminder_offset_minutes", 30),
                            on_change=lambda v: (prefs.set("reminder_offset_minutes", v), app.toast(t("msg.setting_saved"), "success"))))
        self.toggle(r, t("set.reminder_default"), "reminder_default_on", t("common.on"), t("common.off"))
        self.chips(r, t("set.default_priority"), [(k, t("prio." + k)) for k in ("low", "medium", "high")],
                   prefs.get("default_priority"), lambda v: self.pick("default_priority", v, rebuild=False))
        backend = ctx.backend
        if backend.background:
            allowed = backend.notifications_allowed()
            self.label(r, t("set.notif_ok") if allowed else t("set.notif_denied"), muted=False)
            if not allowed:
                r.add_widget(AButton(t("perm.allow"), "primary", icon="bell", on_action=self.ask_permission))
            r.add_widget(AButton(t("set.open_notif_settings"), "secondary", on_action=lambda: self.open_android("notifications")))
            r.add_widget(AButton(t("set.battery"), "secondary", on_action=lambda: self.open_android("battery")))
            self.label(r, t("set.battery_note"), size=12.5)
        else:
            self.label(r, t("set.notif_desktop"), muted=False)
        r.add_widget(AButton(t("set.test_notif"), "tonal", icon="bell", on_action=self.test_notification))

        # ===== Experience =====
        e = self.card(t("set.experience"))
        self.chips(e, t("set.encouragement"), [("off", t("enc_level.off")), ("gentle", t("enc_level.gentle")),
                                               ("normal", t("enc_level.normal"))],
                   prefs.get("encouragement"), lambda v: self.pick("encouragement", v, rebuild=False))
        self.toggle(e, t("set.quiet"), "quiet_mode", t("common.on"), t("common.off"))
        self.label(e, t("set.quiet_note"), size=12.5)
        self.toggle(e, t("set.reduced_motion"), "reduced_motion", t("common.on"), t("common.off"))
        supported = platform_utils.haptics_supported()
        self.toggle(e, t("set.haptics") + ("" if supported else " — " + t("set.unsupported")), "haptics",
                    t("common.on"), t("common.off"), enabled=supported)

        # ===== Data & privacy =====
        d = self.card(t("set.data"))
        self.label(d, t("set.data_note"))
        self.label(d, t("set.data_where", path=str(config.data_dir())), size=12.5)
        d.add_widget(AButton(t("set.backup"), "tonal", icon="download", on_action=self.backup))
        self.restore_path = AInput(t("set.restore_path_hint"))
        d.add_widget(AButton(t("set.restore_pick"), "secondary", icon="upload", on_action=self.pick_backup))
        d.add_widget(rtl_row(self.restore_path, AButton(t("set.restore_btn"), "secondary", on_action=self.restore_from_path,
                                                        size_hint_x=None, width=dp(110)), height=touch(48)))
        d.add_widget(AButton(t("set.export_csv"), "secondary", icon="download", on_action=lambda: self.export("csv")))
        d.add_widget(AButton(t("set.export_json"), "secondary", icon="download", on_action=lambda: self.export("json")))
        d.add_widget(AButton(t("set.reset_prefs"), "secondary", on_action=self.reset_preferences))
        d.add_widget(AButton(t("set.demo_add"), "secondary", on_action=self.add_demo))
        d.add_widget(AButton(t("set.demo_remove"), "secondary", on_action=self.remove_demo))
        d.add_widget(AButton(t("set.delete_all"), "danger", icon="trash", on_action=self.delete_all))

        # ===== About =====
        ab = self.card(t("set.about"))
        self.label(ab, f"SHAHER {__version__}", muted=False, size=15)
        self.label(ab, t("about.desc"))
        self.label(ab, t("about.privacy"))
        from app.database.migrations import get_version
        info = t("about.trouble", mode=textengine.mode(), backend=ctx.backend.name,
                 schema=get_version(ctx.conn), log=str(config.logs_dir() / "shaher.log"))
        self.label(ab, info, size=12)

    # ---------- actions ----------
    def save_name(self):
        self.app.ctx.prefs.set("user_name", self.name_input.text)
        self.app.toast(t("msg.name_saved"), "success")

    def apply_custom_color(self):
        value = self.custom_hex.text.strip()
        if not _valid_hex(value):
            self.app.toast(t("set.custom_invalid"), "error")
            return
        self.app.ctx.prefs.set("custom_accent", value)
        self.pick("accent", "custom")

    def ask_permission(self):
        self.app.ctx.backend.request_permission()
        self.app.toast(t("perm.hint"))

    def open_android(self, kind):
        if not platform_utils.open_android_settings(kind):
            self.app.toast(t("set.open_failed"), "error")

    def test_notification(self):
        ctx = self.app.ctx
        if ctx.backend.background:
            if not ctx.backend.notifications_allowed():
                self.app.toast(t("set.notif_denied"), "error", seconds=4)
                return
            ctx.reminders.send_test()
            self.app.toast(t("set.test_sent"), "success", seconds=4)
        else:
            self.app.toast(t("notif.test_body"), "success")

    def backup(self):
        try:
            path = backup_service.export_backup(self.app.ctx.conn)
            self.app.toast(t("msg.backup_done", name=path.name), "success", seconds=4)
        except Exception:
            self.app.report_unexpected_error(t("msg.backup_failed"))

    def pick_backup(self):
        files = backup_service.list_backups()
        if not files:
            self.app.toast(t("set.no_backups"))
            return
        choose(t("set.restore_pick"), [(str(p), p.name) for p in files[:10]], lambda v: self.confirm_restore(v))

    def restore_from_path(self):
        path = self.restore_path.text.strip().strip('"')
        if not path:
            self.app.toast(t("set.restore_path_empty"), "error")
            return
        self.confirm_restore(path)

    def confirm_restore(self, path):
        try:
            data_service.validate_backup(path)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error", seconds=4)
            return
        confirm(t("set.restore_title"), t("set.restore_message"), lambda: self._do_restore(path), yes_text=t("set.restore_yes"),
                danger=True)

    def _do_restore(self, path):
        ctx = self.app.ctx
        try:
            safety = data_service.restore_backup(ctx.conn, path, ctx.reminders)
        except ValidationError as e:
            self.app.toast(e.errors[0], "error", seconds=4)
            return
        except Exception:
            self.app.report_unexpected_error(t("msg.restore_failed"))
            return
        self.app.reload_preferences(go_to="settings")
        self.app.toast(t("msg.restore_done", name=safety.name), "success", seconds=5)

    def export(self, kind):
        try:
            conn = self.app.ctx.conn
            path = data_service.export_csv(conn) if kind == "csv" else data_service.export_json(conn)
            self.app.toast(t("msg.export_done", path=str(path)), "success", seconds=6)
        except Exception:
            self.app.report_unexpected_error(t("msg.export_failed"))

    def reset_preferences(self):
        def go():
            self.app.ctx.prefs.reset_preferences()
            self.app.reload_preferences(go_to="settings")
            self.app.toast(t("msg.prefs_reset"), "success")
        confirm(t("set.reset_title"), t("set.reset_message"), go, yes_text=t("set.reset_yes"))

    def add_demo(self):
        def go():
            try:
                n = add_demo_data(self.app.ctx.commitments, self.app.ctx.habits)
                self.app.toast(t("msg.demo_added", n=n), "success")
            except ValidationError as e:
                self.app.toast(e.errors[0], "error")
        confirm(t("set.demo_title"), t("set.demo_message"), go, yes_text=t("common.add"))

    def remove_demo(self):
        def go():
            n = remove_demo_data(self.app.ctx.conn, self.app.ctx.reminders)
            self.app.toast(t("msg.demo_removed", n=n) if n else t("msg.demo_none"), "success")
        confirm(t("set.demo_remove"), t("set.demo_remove_message"), go, yes_text=t("common.delete"), danger=True)

    def delete_all(self):
        def second():
            confirm(t("set.delete_all_title2"), t("set.delete_all_message2"), final, yes_text=t("set.delete_all_yes"), danger=True)

        def final():
            data_service.delete_all_data(self.app.ctx.conn, self.app.ctx.reminders)
            self.app.toast(t("msg.all_deleted"), "success")
            self.app.go("home")
        confirm(t("set.delete_all_title"), t("set.delete_all_message"), second, yes_text=t("common.continue"), danger=True)
