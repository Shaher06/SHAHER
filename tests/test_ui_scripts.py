"""Run the real Kivy UI scripts in subprocesses. Skipped when no display is available
(on Linux use:  xvfb-run -a python -m pytest tests/test_ui_scripts.py)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HAS_DISPLAY = sys.platform.startswith("win") or sys.platform == "darwin" or bool(os.environ.get("DISPLAY"))

pytestmark = pytest.mark.skipif(not HAS_DISPLAY, reason="needs a display (use xvfb-run on Linux)")
pytest.importorskip("kivy")


def run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=240)


@pytest.mark.parametrize("lang,theme", [("ar", "light"), ("en", "dark")])
def test_ui_smoke(tmp_path, lang, theme):
    proc = run(["scripts/ui_smoke_test.py", str(tmp_path), lang, theme])
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert "FAIL" not in proc.stdout


def test_settings_survive_an_app_restart():
    proc = run(["scripts/ui_restart_test.py"])
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert "FAIL" not in proc.stdout
