# Changelog

## 2.0.0
### Fixed
- **Arabic rendering.** Letters were drawn disconnected. Cause: the text renderer does not join Arabic letters, and the old font (Cairo) lacked the *isolated* presentation forms needed when joining in Python. Now: `arabic-reshaper` + `python-bidi` applied **only at display time** + bundled IBM Plex Sans Arabic (full coverage). Stored text is never altered.
- (v1 note) The 1.0 "word reordering" approach was based on a mistaken reading of screenshots and is removed.

### Added
- Language selector (Arabic RTL / English LTR) with a translation system and fallbacks; localized dates, optional Arabic digits.
- Design system: light (ivory glass) / dark / system themes, 7 accents + custom colour with automatic contrast correction, density, text size, corner style, decorative background, vector icons.
- First-launch onboarding with optional preferred name.
- New dashboard focused on commitments; Quick Add; sorting; reschedule; weekly overview; Daily Focus & review.
- Contextual encouragement (off / gentle / normal, quiet mode).
- Reminder improvements: configurable defaults, test notification, resync on resume, notification/battery settings shortcuts.
- Backup (existing) + **validated restore** (safety copy first), CSV and JSON export, reset preferences, delete-all workflow.
- Arabic text input that shapes correctly (see docs/ARABIC_VERIFICATION.md).
- Desktop keyboard shortcuts.
- Database migration 3 (`commitments.focus_date`) — additive only.

### Changed
- Font: Cairo → IBM Plex Sans Arabic (Regular + Bold).
- All UI text moved to `app/i18n`; validation errors are translated at display time.
- Dependencies: + `arabic-reshaper==3.0.1`, `python-bidi==0.4.2`, `six`.

### Not done / not verified
- Recurring commitments (not implemented). Windows and Android runs (not tested). APK (not built).
