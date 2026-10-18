# Arabic rendering: cause, fix, verification

## Cause (measured, not guessed)
On the development machine Kivy 2.3.1's text renderer does **no Arabic shaping and no bidirectional layout**:
four joined-form letters measure exactly 4× one isolated letter, and text is laid out strictly left-to-right.
Each letter therefore appears isolated ("disconnected"). In addition the old font (Cairo) has **no isolated
presentation forms** (U+FE8D, FE8F …), so it could not even display Python-shaped text.

> Correction: in SHAHER 1.0 I wrongly concluded that letters were joined and only word order was wrong; that came from
> misreading small screenshots. 2.0 uses pixel measurements instead.

## Fix
`app/utils/arabic.py` → `visual()`: `arabic-reshaper` (contextual forms + lam-alef ligatures) then `python-bidi`
(visual order, paragraph direction = UI language). Applied at the last moment before text reaches a Kivy label
(`ALabel`, `AButton`, `AInput` overlay). **Never applied to values stored in SQLite or to what the keyboard edits.**
Font: IBM Plex Sans Arabic (a test proves it contains every form the reshaper can emit).

Input fields (`AInput`): the real `TextInput` holds the logical text. When it contains Arabic, its own glyphs are hidden
and a shaped overlay is drawn; the caret is kept at the end (mid-text Arabic editing is not supported; a ✕ clears the
field). Latin-only text uses the `TextInput` directly (normal editing).

## Verification done
| Check | How | Result |
|---|---|---|
| Pure logic (forms, order, numbers, Latin, brackets, lam-alef, multiline, wrapping, no mutation) | `tests/test_arabic_rendering.py` | pass |
| Glyph pictures | `tests/test_arabic_visual.py`: our output drawn by a **non-shaping** renderer vs a **real shaping** renderer (Pillow+Raqm) | 8 pure-Arabic samples match (diff ≤ ~10; wrong output scores 20–37); 6 mixed samples match overall width ±4%; a negative control proves the test fails on unprocessed text |
| Mixed text/numbers/dates/filenames | image `docs/images/arabic_mixed_check.png` (black = reference, blue = ours) | order and shapes identical |
| Real Kivy screens | scripted UI run on Linux, screenshots inspected (Arabic + English, light + dark, 360 px, large text) | joined, right-to-left, no clipping seen |
| Both layout directions | same | pass |

## NOT verified
- Windows 11 and Android screens (not available). The pipeline is renderer-independent *if* the renderer draws code points
  as given, which was true on the development machine.
- If a platform's renderer shapes by itself, `Settings → About` shows the probe result; `SHAHER_TEXT_MODE=native`
  can force passthrough. This path is untested.
- Android IME behaviour for Arabic typing (composition, suggestions) and the caret-at-end behaviour on a phone.

## Practical visual checklist (run on Windows and on the phone)
Use the **Demo data** button, then confirm each line by eye:
1. Onboarding title "أهلا بيك، تحب أناديك بإيه؟": letters connected, first word at the right.
2. Type a name "محمد علي" in onboarding: connected while typing; ✕ clears it; greeting "مساء النور، محمد علي".
3. Add a commitment titled `اجتماع مع John Smith الساعة 5` → title shows Arabic joined, "John Smith" intact and readable, "5" in place.
4. Title `تقرير (نسخة 2) - report.pdf`: brackets not flipped wrongly, filename intact.
5. Due labels "اليوم 18:30", "غدًا 09:00", date "الثلاثاء 13 أكتوبر 2026": numbers readable, order right-to-left.
6. Switch to English: layout mirrors (back arrow, nav order, chips start left); an Arabic title still joined inside an English layout.
7. Switch digits to Arabic (Settings → Look and feel): ١٨:٣٠ readable; stored data unchanged (export CSV shows 18:30).
8. Dark mode, large text, compact density: nothing clipped or overlapping.
9. Edit an Arabic title, save, reopen the form: text identical to what you typed; check the CSV export in Excel (UTF-8).
10. Notification text (Android): Arabic reminder shows joined letters in the system notification (this text is NOT reshaped; the OS renders it).
