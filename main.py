"""SHAHER entry point.  Run:  python main.py"""
import logging
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import config                                            # noqa: E402
from app.utils.logging_setup import setup_logging                  # noqa: E402

setup_logging()
log = logging.getLogger("shaher.main")

os.environ.setdefault("KIVY_NO_ARGS", "1")
from kivy.config import Config                                    # noqa: E402

Config.set("kivy", "exit_on_escape", "0")
if not config.is_android():
    Config.set("graphics", "width", os.environ.get("SHAHER_WIDTH", "420"))
    Config.set("graphics", "height", os.environ.get("SHAHER_HEIGHT", "800"))
    Config.set("graphics", "resizable", "1")

from kivy.app import App                                          # noqa: E402
from kivy.clock import Clock                                      # noqa: E402
from kivy.core.window import Window                               # noqa: E402
from kivy.uix.boxlayout import BoxLayout                           # noqa: E402
from kivy.uix.floatlayout import FloatLayout                       # noqa: E402
from kivy.uix.screenmanager import FadeTransition, NoTransition, ScreenManager  # noqa: E402

from app import i18n                                              # noqa: E402
from app.database.db import connect                                # noqa: E402
from app.i18n import t                                            # noqa: E402
from app.services.commitment_service import CommitmentService      # noqa: E402
from app.services.encouragement import Encourager                  # noqa: E402
from app.services.habit_service import HabitService                # noqa: E402
from app.services.preferences import Preferences                   # noqa: E402
from app.services.reminder_backends import default_backend         # noqa: E402
from app.services.reminder_service import ReminderService          # noqa: E402
from app.services.settings_service import SettingsService          # noqa: E402
from app.utils import arabic, dates, platform_utils                # noqa: E402
from app.utils.validation import ValidationError                   # noqa: E402
from app.widgets import common, textengine, theme                  # noqa: E402

theme.register_fonts()

from app.screens.commitment_form import CommitmentFormScreen      # noqa: E402
from app.screens.commitments import CommitmentsScreen            # noqa: E402
from app.screens.habits import HabitDetailScreen, HabitFormScreen, HabitsScreen  # noqa: E402
from app.screens.home import HomeScreen                           # noqa: E402
from app.screens.onboarding import OnboardingScreen              # noqa: E402
from app.screens.review import ReviewScreen                      # noqa: E402
from app.screens.settings import SettingsScreen                  # noqa: E402
from app.screens.week import WeekScreen                          # noqa: E402
from app.widgets.common import ALabel, AButton, Backdrop         # noqa: E402
from app.widgets.dialogs import Dialog, toast                    # noqa: E402
from app.widgets.nav import NavBar                               # noqa: E402
from app.widgets.theme import dp, fs                             # noqa: E402

HIDE_NAV = {"commitment_form", "habit_form", "habit_detail", "onboarding", "review"}
NAV_OF = {"home": "home", "commitments": "commitments", "commitment_form": "commitments", "week": "week",
          "habits": "habits", "habit_detail": "habits", "habit_form": "habits", "settings": "settings", "review": "home"}


@dataclass
class AppContext:
    conn: object
    settings: SettingsService
    prefs: Preferences
    backend: object
    reminders: ReminderService
    commitments: CommitmentService
    habits: HabitService
    encourager: Encourager


def build_context(db_path=None) -> AppContext:
    conn = connect(db_path)
    settings = SettingsService(conn)
    backend = default_backend()
    reminders = ReminderService(conn, backend)
    commitments = CommitmentService(conn, reminders)
    prefs = Preferences(settings)
    return AppContext(conn, settings, prefs, backend, reminders, commitments, HabitService(conn, reminders),
                      Encourager(prefs, commitments))


def apply_preferences(prefs: Preferences) -> None:
    """Push the stored preferences into language, text engine, theme and widget flags."""
    i18n.set_language(prefs.get("language"))
    i18n.set_arabic_digits(prefs.get("digits") == "arabic")
    arabic.set_base_direction(i18n.is_rtl())
    theme.apply(prefs.get("theme_mode"), prefs.get("accent"), prefs.get("custom_accent"), prefs.get("density"),
                prefs.get("text_scale"), prefs.get("radius"), prefs.flag("decor"), platform_utils.system_theme())
    common.HAPTICS["on"] = prefs.flag("haptics") and platform_utils.haptics_supported()
    common.REDUCED_MOTION["on"] = prefs.flag("reduced_motion")
    Window.clearcolor = theme.BG


class ShaherApp(App):
    title = "SHAHER"

    def __init__(self, ctx: AppContext = None, **kwargs):
        super().__init__(**kwargs)
        self._ctx = ctx

    # ---------- construction ----------
    def build(self):
        self.ctx = self._ctx or build_context()
        textengine.configure()
        apply_preferences(self.ctx.prefs)
        if config.is_android():
            Window.softinput_mode = "below_target"
        icon = config.project_root() / "assets" / "icons" / "icon.png"
        if icon.exists():
            self.icon = str(icon)
        self.holder = FloatLayout()
        self.rebuild()
        Window.bind(on_keyboard=self._on_key)
        if not config.is_android():
            Window.bind(on_key_down=self._on_shortcut)
        return self.holder

    def rebuild(self, go_to=None):
        """(Re)create every screen so a language/theme/density change applies everywhere."""
        Window.clearcolor = theme.BG
        self.holder.clear_widgets()
        self.holder.add_widget(Backdrop())
        column = BoxLayout(orientation="vertical")
        reduced = self.ctx.prefs.flag("reduced_motion")
        self.sm = ScreenManager(transition=NoTransition() if reduced else FadeTransition(duration=0.15))
        self.screens = {
            "home": HomeScreen(self, name="home"),
            "commitments": CommitmentsScreen(self, name="commitments"),
            "commitment_form": CommitmentFormScreen(self, name="commitment_form"),
            "week": WeekScreen(self, name="week"),
            "review": ReviewScreen(self, name="review"),
            "habits": HabitsScreen(self, name="habits"),
            "habit_detail": HabitDetailScreen(self, name="habit_detail"),
            "habit_form": HabitFormScreen(self, name="habit_form"),
            "settings": SettingsScreen(self, name="settings"),
            "onboarding": OnboardingScreen(self, name="onboarding"),
        }
        for s in self.screens.values():
            self.sm.add_widget(s)
        column.add_widget(self.sm)
        self.nav = NavBar(self.go)
        column.add_widget(self.nav)
        self.holder.add_widget(column)
        self.sm.bind(current=self._on_screen_change)
        target = "onboarding" if self.ctx.prefs.needs_onboarding else (go_to or "home")
        self.sm.current = target
        self.screens[target].refresh()
        self._on_screen_change()

    def set_preference(self, name, value, rebuild_to=None):
        self.ctx.prefs.set(name, value)
        apply_preferences(self.ctx.prefs)
        if name == "language":
            try:
                self.ctx.reminders.resync_all()      # notification texts follow the language
            except Exception:
                log.exception("resync after language change failed")
        if rebuild_to:
            self.rebuild(rebuild_to)

    def reload_preferences(self, go_to="home"):
        apply_preferences(self.ctx.prefs)
        self.rebuild(go_to)

    def finish_onboarding(self, name):
        self.ctx.prefs.set("user_name", name)
        self.ctx.prefs.set("onboarded", "1")
        self.ctx.encourager.mark_opened()
        self.rebuild("home")

    # ---------- navigation ----------
    def go(self, name):
        self.sm.current = name

    def _on_screen_change(self, *_):
        current = self.sm.current
        hidden = current in HIDE_NAV
        self.nav.height = 0 if hidden else dp(64)
        self.nav.opacity = 0 if hidden else 1
        self.nav.disabled = hidden
        self.nav.set_active(NAV_OF.get(current, "home"))

    def show_commitments(self, view):
        self.screens["commitments"].view = view
        self.go("commitments")

    def open_commitment_form(self, item, due=None):
        self.screens["commitment_form"].load(item, due)
        self.go("commitment_form")

    def open_habit(self, habit_id):
        self.screens["habit_detail"].load(habit_id)
        self.go("habit_detail")
        self.screens["habit_detail"].refresh()

    def open_habit_form(self, habit_id):
        habit = self.ctx.habits.get(habit_id) if habit_id else None
        self.screens["habit_form"].load(habit)
        self.screens["habit_form"].back_target = "habit_detail" if habit else "habits"
        self.go("habit_form")

    def _on_key(self, window, key, *args):
        if key == 27:                                # Android back button / Esc
            current = self.sm.current
            screen = self.screens.get(current)
            if current in HIDE_NAV and current != "onboarding":
                screen.go_back()
                return True
            if current not in ("home", "onboarding"):
                self.go("home")
                return True
        return False

    def _on_shortcut(self, window, key, scancode, codepoint, modifiers):
        """Desktop only: Ctrl+N new commitment, Ctrl+F search, Ctrl+1..5 switch tab."""
        if "ctrl" not in modifiers or self.sm.current == "onboarding":
            return False
        if codepoint == "n":
            self.open_commitment_form(None)
            return True
        if codepoint == "f":
            self.go("commitments")
            Clock.schedule_once(lambda dt: self.screens["commitments"].focus_search(), 0.1)
            return True
        tabs = {"1": "home", "2": "commitments", "3": "week", "4": "habits", "5": "settings"}
        if codepoint in tabs:
            self.go(tabs[codepoint])
            return True
        return False

    # ---------- shared behaviours ----------
    def toast(self, message, kind="info", seconds=2.8):
        toast(message, kind, seconds)

    def run_action(self, fn, ok_message, after=None):
        try:
            fn()
        except ValidationError as e:
            self.toast(e.errors[0], "error")
        except Exception:
            self.report_unexpected_error(t("msg.unexpected"))
            return
        else:
            self.toast(ok_message, "success")
        if after:
            after()

    def complete_commitment(self, item, after=None):
        """Complete, then show a short, contextual encouragement (or the plain confirmation)."""
        try:
            self.ctx.commitments.complete(item.id)
        except ValidationError as e:
            self.toast(e.errors[0], "error")
            return
        except Exception:
            self.report_unexpected_error(t("msg.unexpected"))
            return
        msg = self.ctx.encourager.on_completed()
        self.toast(t(msg[0], **msg[1]) if msg else t("msg.completed"), "success")
        if after:
            after()

    def report_unexpected_error(self, message):
        log.exception(message)
        self.toast(message + " " + t("msg.no_data_lost"), "error", seconds=5)

    # ---------- lifecycle ----------
    def on_start(self):
        try:
            self.ctx.reminders.resync_all()          # keep scheduled reminders in step with the database
        except Exception:
            log.exception("reminder resync failed")
        if not self.ctx.backend.background:
            Clock.schedule_interval(self._poll_in_app_reminders, 20)
        if not self.ctx.prefs.get("last_open_date"):
            self.ctx.encourager.mark_opened()
        log.info("SHAHER started (reminders: %s, text mode: %s)", self.ctx.backend.name, textengine.mode())

    def on_pause(self):
        self.ctx.encourager.mark_opened()
        return True

    def on_stop(self):
        self.ctx.encourager.mark_opened()

    def on_resume(self):
        """Clock/timezone/system-theme may have changed while we were away."""
        try:
            self.ctx.reminders.resync_all()
        except Exception:
            log.exception("reminder resync failed")
        if self.ctx.prefs.get("theme_mode") == "system" and platform_utils.system_theme() != theme.MODE:
            apply_preferences(self.ctx.prefs)
            self.rebuild(self.sm.current)

    def _poll_in_app_reminders(self, dt):
        try:
            for item in self.ctx.reminders.due_in_app():
                self.ctx.reminders.mark_shown(item.id)
                dlg = Dialog(t("reminder.title"))
                dlg.add_widget(ALabel(item.title, font_size=fs(18), bold=True))
                dlg.add_widget(ALabel(t("notif.commitment_body", when=dates.friendly_due(item.due_at, self.ctx.commitments.now().date())),
                                      color=theme.MUTED))
                dlg.add_widget(AButton(t("common.ok"), "primary", on_action=dlg.dismiss))
                dlg.open()
        except Exception:
            log.exception("in-app reminder check failed")


if __name__ == "__main__":
    try:
        ShaherApp().run()
    except Exception:
        log.exception("fatal error")
        raise
