"""Launch the real app twice against the same data folder to prove preferences persist.

    xvfb-run -a python scripts/ui_restart_test.py            (Linux)   |   python scripts\\ui_restart_test.py   (Windows)

Phase 1 onboards and changes language/theme/accent/name; phase 2 is a fresh process that must
come up with the same settings and must NOT show onboarding again.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def phase(which: str, data_dir: str) -> None:
    os.environ["SHAHER_DATA_DIR"] = data_dir
    sys.path.insert(0, str(ROOT))
    import main
    from kivy.base import stopTouchApp
    from kivy.clock import Clock
    from app import i18n
    from app.widgets import theme
    result = {}

    class A(main.ShaherApp):
        def on_start(self):
            super().on_start()
            Clock.schedule_once(self.step, 0.6)

        def step(self, dt):
            if which == "one":
                result["onboarding_first"] = self.sm.current == "onboarding"
                self.finish_onboarding("سارة")
                self.set_preference("language", "en", rebuild_to="home")
                self.set_preference("theme_mode", "dark", rebuild_to="home")
                self.set_preference("accent", "violet", rebuild_to="home")
                self.set_preference("density", "compact", rebuild_to="home")
                self.set_preference("text_scale", "large", rebuild_to="home")
                self.ctx.commitments.create("Persisted item", "", __import__("datetime").datetime.now().replace(second=0, microsecond=0)
                                            + __import__("datetime").timedelta(days=2))
            else:
                result.update(screen=self.sm.current, language=i18n.language(), mode=theme.MODE,
                              accent=self.ctx.prefs.get("accent"), name=self.ctx.prefs.get("user_name"),
                              density=theme.DENSITY, text_scale=theme.TEXT_SCALE,
                              items=[c.title for c in self.ctx.commitments.list("all")])
            stopTouchApp()

    A().run()
    print("RESULT_JSON " + json.dumps(result, ensure_ascii=False))


def main_driver() -> int:
    data_dir = tempfile.mkdtemp(prefix="shaher_restart_")
    outputs = []
    for which in ("one", "two"):
        proc = subprocess.run([sys.executable, __file__, which, data_dir], capture_output=True, text=True, encoding="utf-8")
        line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT_JSON ")]
        if proc.returncode != 0 or not line:
            print(proc.stdout[-1500:], proc.stderr[-1500:])
            return 1
        outputs.append(json.loads(line[0][len("RESULT_JSON "):]))
    first, second = outputs
    checks = {
        "onboarding shown on first launch": first.get("onboarding_first") is True,
        "second launch skips onboarding": second["screen"] == "home",
        "language persisted": second["language"] == "en",
        "theme persisted": second["mode"] == "dark",
        "accent persisted": second["accent"] == "violet",
        "name persisted": second["name"] == "سارة",
        "density persisted": second["density"] < 1,
        "text size persisted": second["text_scale"] > 1,
        "data persisted": second["items"] == ["Persisted item"],
    }
    for name, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + name)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("one", "two"):
        phase(sys.argv[1], sys.argv[2])
    else:
        sys.exit(main_driver())
