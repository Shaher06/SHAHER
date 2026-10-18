"""Drive the real Kivy UI headlessly and save screenshots.

    xvfb-run -a python scripts/ui_smoke_test.py OUT_DIR [lang] [theme] [width] [height]

    lang  = ar | en           theme = light | dark | system
Uses a temporary data folder, never your real database. Exit code 0 = every check passed.
"""
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
LANG = sys.argv[2] if len(sys.argv) > 2 else "ar"
THEME = sys.argv[3] if len(sys.argv) > 3 else "light"
os.environ["SHAHER_WIDTH"] = sys.argv[4] if len(sys.argv) > 4 else "420"
os.environ["SHAHER_HEIGHT"] = sys.argv[5] if len(sys.argv) > 5 else "800"
tmp = tempfile.mkdtemp(prefix="shaher_ui_")
os.environ["SHAHER_DATA_DIR"] = tmp
OUT.mkdir(parents=True, exist_ok=True)

import main  # noqa: E402
from kivy.base import EventLoop, stopTouchApp  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402

from app import i18n  # noqa: E402
from app.services.demo_data import add_demo_data  # noqa: E402

failures = []
tag = f"{LANG}_{THEME}" + ("_large" if os.environ.get("SHAHER_TEST_TEXT") == "large" else "") + ("_" + os.environ.get("SHAHER_WIDTH", "420"))


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def pump(n=8):
    for _ in range(n):
        Clock.tick()
        EventLoop.idle()


def shot(name, scroll=None, screen=None):
    if screen is not None and scroll is not None:
        screen.scroll.scroll_y = scroll
    pump(10)
    Window.screenshot(str(OUT / f"{tag}_{name}.png"))


def visible_buttons(widget, found=None):
    """All AButton/IconButton/Chip widgets under `widget` (to prove none are inert)."""
    from app.widgets.common import AButton, IconButton
    found = [] if found is None else found
    for child in widget.children:
        if isinstance(child, (AButton, IconButton)):
            found.append(child)
        visible_buttons(child, found)
    return found


def run(app, dt):
    try:
        ctx = app.ctx
        check(app.sm.current == "onboarding", "first launch shows onboarding")
        shot("00_onboarding")
        onboarding = app.screens["onboarding"]
        onboarding.name_input.text = "محمد" if LANG == "ar" else "Sara"
        pump()
        shot("01_onboarding_name")
        onboarding.start()
        pump()
        check(app.sm.current == "home" and ctx.prefs.get("user_name") in ("محمد", "Sara"), "name saved, home shown")
        check(not ctx.prefs.needs_onboarding, "onboarding will not appear again")
        shot("02_home_empty")

        home = app.screens["home"]
        home.quick.text = "اتصال بالمدير" if LANG == "ar" else "Call the manager"
        home._quick_add()
        pump()
        check(len(ctx.commitments.list("all")) == 1, "quick add creates one commitment")
        add_demo_data(ctx.commitments, ctx.habits)
        home.refresh(); shot("03_home")
        shot("03b_home_scrolled", 0.0, home)

        app.open_commitment_form(None)
        form = app.screens["commitment_form"]
        form.title_field.text = "اجتماع مع المدير" if LANG == "ar" else "Meeting with the manager"
        form.desc_field.text = "تجهيز التقرير الشهري والأرقام" if LANG == "ar" else "Prepare the monthly report"
        form.category_field.text = "عمل" if LANG == "ar" else "Work"
        form.set_priority("high")
        form.toggle_reminder()
        due = ctx.commitments.now() + timedelta(days=1)
        form.when.set_datetime(due.replace(hour=10, minute=0))
        shot("04_form")
        shot("04b_form_bottom", 0.0, form)
        form.save(); form.save()
        pump()
        check(len([c for c in ctx.commitments.list("all") if c.title.startswith(("اجتماع", "Meeting"))]) == 1, "form saved exactly once")

        app.show_commitments("all"); shot("05_commitments")
        app.show_commitments("overdue"); shot("06_overdue")
        app.go("week"); shot("07_week")
        app.go("review"); shot("08_review")
        app.go("habits"); shot("09_habits")
        habit = ctx.habits.list()[0]
        app.open_habit(habit.id); shot("10_habit_detail")
        for i, pos in enumerate((1.0, 0.55, 0.0)):
            app.go("settings"); shot(f"11_settings_{i}", pos, app.screens["settings"])

        # every visible button must have an action
        inert = []
        for name, screen in app.screens.items():
            if name == "onboarding":
                continue
            app.go(name) if name not in ("habit_detail", "habit_form", "commitment_form") else None
            pump(3)
            for b in visible_buttons(screen):
                if getattr(b, "_action", None) is None and type(b).__name__ in ("AButton", "IconButton"):
                    inert.append((name, b.raw if hasattr(b, "raw") else "icon"))
        check(not inert, f"no inert buttons ({inert})")

        # language switch keeps data and flips direction
        before = len(ctx.commitments.list("all"))
        other = "en" if LANG == "ar" else "ar"
        app.set_preference("language", other, rebuild_to="settings")
        pump()
        check(i18n.language() == other and len(ctx.commitments.list("all")) == before, "language switch keeps data")
        shot("12_after_language_switch")
        app.set_preference("language", LANG, rebuild_to="home")
        # accent + theme switch
        app.set_preference("accent", "violet", rebuild_to="settings"); pump(); shot("13_violet", 1.0, app.screens["settings"])
        check(ctx.prefs.get("accent") == "violet", "accent persisted")
        app.set_preference("accent", "teal", rebuild_to="home")
        app.go("home")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        failures.append(repr(exc))
    finally:
        stopTouchApp()


class TestApp(main.ShaherApp):
    def on_start(self):
        super().on_start()
        Clock.schedule_once(lambda dt: run(self, dt), 0.8)


if __name__ == "__main__":
    ctx = main.build_context(Path(tmp) / "ui_test.db")
    ctx.prefs.set("language", LANG)
    ctx.prefs.set("theme_mode", THEME)
    ctx.prefs.set("text_scale", os.environ.get("SHAHER_TEST_TEXT", "standard"))   # standard | large
    ctx.prefs.set("density", os.environ.get("SHAHER_TEST_DENSITY", "comfortable"))  # comfortable | compact
    TestApp(ctx=ctx).run()
    print("RESULT:", "FAILED " + str(failures) if failures else "all UI smoke checks passed", "|", OUT)
    sys.exit(1 if failures else 0)
