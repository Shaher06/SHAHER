import glob
import re
import string
from pathlib import Path

import pytest

from app import i18n
from app.i18n.strings_ar import STRINGS as AR
from app.i18n.strings_en import STRINGS as EN

ROOT = Path(__file__).resolve().parent.parent
DYNAMIC_PREFIXES = {"prio.": ("low", "medium", "high"), "offset.": ("0", "10", "30", "60", "1440"),
                    "view.": ("all", "overdue", "today", "upcoming", "completed", "archived")}


@pytest.fixture(autouse=True)
def restore_language():
    yield
    i18n.set_language("ar")
    i18n.set_arabic_digits(False)


def used_keys():
    keys = set()
    for path in glob.glob(str(ROOT / "**" / "*.py"), recursive=True):
        if "/tests/" in path or "/i18n/" in path or "/scripts/" in path:
            continue
        src = open(path, encoding="utf-8").read()
        keys |= set(re.findall(r'\bt\(\s*"([a-z_0-9.]+[a-z_0-9])"', src))
        keys |= set(re.findall(r'"((?:err|enc|notif|due|greet)\.[a-z_0-9]+)"', src))
        keys |= set(re.findall(r'(?:title_key\s*=\s*)"([a-z_0-9.]+)"', src))
        keys |= {f"{p}{v}" for p, vals in DYNAMIC_PREFIXES.items() for v in vals}
    for view in ("all", "overdue", "today", "upcoming", "completed", "archived"):
        keys |= {f"empty.{view}", f"empty.{view}_hint"}
    return keys


def test_both_languages_define_the_same_keys():
    assert set(AR) == set(EN), (sorted(set(AR) ^ set(EN)))


def test_every_key_used_in_code_exists_in_both_languages():
    missing = sorted(k for k in used_keys() if k not in AR or k not in EN)
    assert not missing, missing


def test_placeholders_match_between_languages():
    def fields(text):
        return {f for _, f, _, _ in string.Formatter().parse(text) if f}
    bad = {k: (fields(AR[k]), fields(EN[k])) for k in AR if fields(AR[k]) != fields(EN[k])}
    assert not bad, bad


def test_no_empty_translations():
    assert not [k for k, v in {**AR, **{"en." + k: v for k, v in EN.items()}}.items() if not v.strip()]


def test_arabic_strings_contain_arabic_and_english_ones_do_not():
    from app.utils.arabic import has_arabic
    exceptions = {"notif.test_title"}
    assert all(has_arabic(v) for k, v in AR.items() if k not in exceptions and not re.fullmatch(r"[\W\d{}a-z]*", v))
    assert not [k for k, v in EN.items() if has_arabic(v)]


def test_switching_language_changes_output_and_fallback_works():
    i18n.set_language("en")
    assert i18n.t("common.save") == "Save" and not i18n.is_rtl()
    i18n.set_language("ar")
    assert i18n.t("common.save") == "حفظ" and i18n.is_rtl()
    assert i18n.t("no.such.key") == "no.such.key"           # never crashes
    assert i18n.t("home.progress", done=2, total=5)       # parameters filled
    assert i18n.t("home.progress") != ""                    # missing parameters: text returned untouched


def test_unknown_language_falls_back_to_arabic():
    i18n.set_language("fr")
    assert i18n.language() == "ar"


def test_arabic_digits_are_display_only():
    i18n.set_arabic_digits(True)
    assert i18n.localize_digits("15:30") == "١٥:٣٠"
    i18n.set_language("en")
    assert i18n.localize_digits("15:30") == "15:30"


def test_dates_follow_the_language():
    from datetime import date, datetime
    from app.utils import dates
    d = date(2026, 10, 13)
    i18n.set_language("ar")
    assert dates.format_date(d) == "الثلاثاء 13 أكتوبر 2026"
    assert dates.friendly_due(datetime(2026, 10, 14, 9, 0), d) == "غدًا 09:00"
    i18n.set_language("en")
    assert dates.format_date(d) == "Tuesday, 13 October 2026"
    assert dates.friendly_due(datetime(2026, 10, 14, 9, 0), d) == "Tomorrow 09:00"
    assert dates.friendly_due(datetime(2026, 10, 20, 9, 0), d) == "20 October 09:00"


def test_validation_errors_are_translated_at_display_time():
    from app.utils.validation import ValidationError
    err = ValidationError("err.title_required")
    i18n.set_language("ar")
    assert "عنوان" in err.errors[0]
    i18n.set_language("en")
    assert "title" in err.errors[0].lower()
