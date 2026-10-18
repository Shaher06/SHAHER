from datetime import datetime, timedelta

import pytest

from app.database.db import connect
from app.services.encouragement import Encourager
from app.services.preferences import Preferences
from app.services.quick_add import default_due, quick_add
from app.services.settings_service import SettingsService

D = datetime


@pytest.fixture
def prefs(conn):
    return Preferences(SettingsService(conn))


def test_defaults(prefs):
    assert prefs.get("language") == "ar" and prefs.get("theme_mode") == "light"
    assert prefs.get("accent") == "teal" and prefs.get("encouragement") == "normal"
    assert prefs.needs_onboarding and prefs.get("user_name") == ""


@pytest.mark.parametrize("name,value", [("language", "en"), ("theme_mode", "dark"), ("theme_mode", "system"),
                                        ("accent", "violet"), ("density", "compact"), ("text_scale", "large"),
                                        ("radius", "round"), ("digits", "arabic"), ("encouragement", "gentle"),
                                        ("default_priority", "high"), ("sort", "priority")])
def test_preferences_persist_across_restart(db_path, name, value):
    first = connect(db_path)
    Preferences(SettingsService(first)).set(name, value)
    first.close()
    again = Preferences(SettingsService(connect(db_path)))          # a "new app launch"
    assert again.get(name) == value


def test_flags_and_name_persist(db_path):
    c1 = connect(db_path)
    p = Preferences(SettingsService(c1))
    p.set("user_name", "  محمد   علي ")
    p.set_flag("quiet_mode", True)
    p.set("onboarded", "1")
    c1.close()
    p2 = Preferences(SettingsService(connect(db_path)))
    assert p2.get("user_name") == "محمد علي" and p2.flag("quiet_mode") and not p2.needs_onboarding


def test_invalid_values_are_rejected_and_bad_stored_values_fall_back(prefs, conn):
    with pytest.raises(ValueError):
        prefs.set("theme_mode", "neon")
    with pytest.raises(ValueError):
        prefs.set("custom_accent", "red")
    conn.execute("INSERT INTO settings(key, value) VALUES('accent', 'garbage')")
    assert prefs.get("accent") == "teal"          # malformed stored value -> default


def test_custom_accent_hex(prefs):
    prefs.set("custom_accent", "#1fa89b")
    assert prefs.get("custom_accent") == "#1fa89b"


def test_name_is_length_limited(prefs):
    prefs.set("user_name", "x" * 200)
    assert len(prefs.get("user_name")) == 30


def test_name_can_be_changed_and_cleared(prefs):
    prefs.set("user_name", "Sara")
    prefs.set("user_name", "")
    assert prefs.get("user_name") == ""


def test_reset_preferences_keeps_data_name_and_onboarding(conn, commitments, prefs):
    commitments.create("مهمة", "", D(2026, 10, 20, 9, 0))
    prefs.set("language", "en"); prefs.set("theme_mode", "dark"); prefs.set("user_name", "Sara"); prefs.set("onboarded", "1")
    prefs.reset_preferences()
    assert prefs.get("language") == "ar" and prefs.get("theme_mode") == "light"
    assert prefs.get("user_name") == "Sara" and not prefs.needs_onboarding
    assert len(commitments.list("all")) == 1                        # data untouched


# ---------------- quick add ----------------
def test_default_due_next_hour_or_tomorrow_morning():
    assert default_due(D(2026, 10, 13, 14, 20)) == D(2026, 10, 13, 15, 0)
    assert default_due(D(2026, 10, 13, 23, 10)) == D(2026, 10, 14, 9, 0)
    assert default_due(D(2026, 10, 13, 22, 59)) == D(2026, 10, 14, 9, 0)


def test_quick_add_uses_defaults(commitments, prefs, backend):
    prefs.set("default_priority", "high")
    prefs.set_flag("reminder_default_on", True)
    prefs.set("reminder_offset_minutes", "10")
    item = quick_add(commitments, prefs, "اتصال بالمدير")       # clock fixture: Tue 12:00
    assert item.due_at == D(2026, 10, 13, 13, 0) and item.priority == "high"
    assert item.reminder_enabled and item.reminder_at == D(2026, 10, 13, 12, 50)
    assert f"c{item.id}" in backend.scheduled


def test_quick_add_without_reminder_default_and_with_empty_title(commitments, prefs):
    assert not quick_add(commitments, prefs, "x").reminder_enabled
    from app.utils.validation import ValidationError
    with pytest.raises(ValidationError):
        quick_add(commitments, prefs, "   ")


# ---------------- encouragement ----------------
@pytest.fixture
def enc(prefs, commitments, clock):
    return Encourager(prefs, commitments, clock.now)


def test_completion_message_is_real_and_not_repeated_back_to_back(enc, commitments, clock):
    a = commitments.create("أ", "", D(2026, 10, 13, 20, 0)); b = commitments.create("ب", "", D(2026, 10, 13, 21, 0))
    c = commitments.create("ج", "", D(2026, 10, 13, 22, 0))
    commitments.complete(a.id)
    first = enc.on_completed()
    commitments.complete(b.id)
    second = enc.on_completed()
    assert first[0] != second[0]                                    # varied, no copy-paste praise
    commitments.complete(c.id)
    assert enc.on_completed()[0] == "enc.all_done"                  # nothing left today


def test_milestone_message_is_not_repeated_immediately(enc, commitments):
    for i in range(3):
        item = commitments.create(f"م{i}", "", D(2026, 10, 14, 9 + i, 0))      # all due tomorrow
        commitments.complete(item.id)
    first = enc.on_completed()
    commitments.complete(commitments.create("م9", "", D(2026, 10, 14, 15, 0)).id)
    assert first is not None and enc.on_completed() is None


def test_all_done_message_only_when_nothing_remains(enc, commitments):
    a = commitments.create("أ", "", D(2026, 10, 13, 20, 0))
    commitments.create("ب", "", D(2026, 10, 13, 21, 0))
    commitments.complete(a.id)
    assert enc.on_completed()[0] != "enc.all_done"


def test_quiet_mode_and_off_silence_everything(enc, prefs, commitments):
    a = commitments.create("أ", "", D(2026, 10, 14, 9, 0))
    commitments.complete(a.id)
    prefs.set_flag("quiet_mode", True)
    assert enc.on_completed() is None and enc.home_message() is None
    prefs.set_flag("quiet_mode", False); prefs.set("encouragement", "off")
    assert enc.on_completed() is None and enc.home_message() is None


def test_gentle_level_is_rarer(enc, prefs, commitments):
    prefs.set("encouragement", "gentle")
    shown = 0
    for i in range(6):
        item = commitments.create(f"م{i}", "", D(2026, 10, 14, 9 + i, 0))
        commitments.complete(item.id)
        shown += enc.on_completed() is not None
    assert shown < 6


def test_home_message_states(enc, commitments, prefs, clock):
    assert enc.home_message()[0] == "enc.calm"                      # nothing urgent
    for i in range(4):
        commitments.create(f"م{i}", "", D(2026, 10, 13, 13 + i, 0))
    key, params = enc.home_message()
    assert key == "enc.busy" and params["n"] == 4                   # real count, not invented


def test_overdue_message_is_a_gentle_offer_not_blame(enc, commitments):
    commitments.create("فات", "", D(2026, 10, 12, 9, 0))
    assert enc.home_message() == ("enc.overdue_soft", {"n": 1})


def test_welcome_back_after_a_break(enc, prefs, clock):
    prefs.set("last_open_date", "2026-10-05")
    assert enc.home_message()[0] == "enc.welcome_back"
    enc.mark_opened()
    assert enc.home_message()[0] != "enc.welcome_back"


def test_encouragement_texts_never_shame(monkeypatch):
    from app.i18n.strings_ar import STRINGS as AR
    from app.i18n.strings_en import STRINGS as EN
    banned_ar = ("فشل", "كسول", "إهمال", "مقصر", "خسارة")
    banned_en = ("fail", "lazy", "behind", "should have", "disappoint", "streak lost")
    for key in [k for k in AR if k.startswith("enc.")]:
        assert not any(w in AR[key] for w in banned_ar), key
        assert not any(w in EN[key].lower() for w in banned_en), key
