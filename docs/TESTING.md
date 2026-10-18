# Testing (SHAHER 2.0)

## Results (Linux, Python 3.12, Kivy 2.3.1, virtual display)
```
xvfb-run -a python -m pytest tests -q     ->  200 passed
python -m pytest tests -q (no display)   ->  197 passed, 3 skipped (the 3 real-UI tests need a display)
```
Baseline before this work: 73 tests. All 73 original tests still pass unchanged except two obsolete Arabic-order tests
that tested the removed word-reordering helper; they were replaced by the stricter tests below (not weakened).
No warnings are produced.

| File | Tests | Covers |
|---|---|---|
| test_commitments.py | 17 | create/edit/complete/reopen, overdue boundary, partitions, search/filters, persistence |
| test_database.py | 9 | schema, migrations, foreign keys, transactions, SQL-injection text stored as data |
| test_habits.py | 27 | streaks, setbacks, corrections, midnight boundary, independence |
| test_reminders.py | 7 | schedule/cancel/reschedule, resync, in-app fallback, no duplicates |
| test_utils_and_services.py | 11 | dates, validation, settings, backup, demo data |
| test_planning.py | 10 | reschedule (reminder lead time kept / disabled if past), reschedule_many, daily focus, progress, week overview, sorting |
| test_preferences.py | 30 | defaults, **persistence after restart** (language, theme, accent, density, text size, radius, digits, encouragement …), name, reset keeps data, quick add, **encouragement** (real data, quiet mode, gentle, no repetition, no-shaming wording) |
| test_data_service.py | 16 | backup→delete→restore round trip, safety copy, invalid/garbage/newer/older backups, preferences restored, CSV (BOM, quotes, Arabic), JSON, delete-all, **migration v3 keeps existing data** |
| test_i18n.py | 10 | both languages same keys, every key used in code exists, placeholders match, fallbacks, localized dates/digits, translated errors |
| test_theme.py | 30 | contrast ≥ 4.5:1 for text/accent/danger/warning in every mode × accent, custom colours always corrected, system mode, density/scale/radius |
| test_arabic_rendering.py | 12 | shaping forms, RTL order, numbers/Latin/brackets, LTR UI, no mutation, wrapping |
| test_arabic_visual.py | 18 | pixel comparison vs a real shaping renderer + negative control + font coverage |
| test_ui_scripts.py | 3 | real Kivy app: smoke in (ar, light) and (en, dark); **restart persistence** |

## Real-UI scripts
- `scripts/ui_smoke_test.py OUT lang theme [w h]` — onboarding, quick add, form (double-save = one row), validation, demo data, week, review, habits, settings, **checks that no visible button is inert**, language switch keeps data, accent persists. Ran for ar/en × light/dark at 420×800, and 360×640 with large text and compact density.
- `scripts/ui_restart_test.py` — two separate app launches on one data folder: onboarding only once; language, theme, accent, name, density, text size and data persist.

## Mapping to the acceptance list
1 launches (Linux virtual display ✔; **Windows not tested**) · 2–5 existing tests ✔ · 6 language persistence ✔ · 7 theme persistence ✔ · 8 accent/appearance persistence ✔ · 9 onboarding only when appropriate ✔ · 10 name persists/changeable ✔ (changing in Settings: covered by service test + UI) · 11 contextual encouragement + quiet mode ✔ · 12 migrations keep data ✔ · 13 backup/restore ✔ · 14 no inert buttons ✔ (scripted check) · 15 Arabic visual ✔ on Linux only · 16 Android config checked against the p4a recipe list and spec syntax, **not built** · 17 **Android reminders unverified**.

## Android device tests still required
See docs/ANDROID_BUILD.md ("What to test on a device").
