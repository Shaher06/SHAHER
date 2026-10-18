# Building the Android APK

**Status: no APK has been built or tested.** The authoring environment could not reach the Android SDK, Gradle or Maven.
The configuration was checked against python-for-android's recipe list and `buildozer.spec` syntax only. Expect to fix small issues on the first build.

## Environment
Linux or **WSL2 (Ubuntu 22.04/24.04)**. Keep the project in the Linux file system (`~/SHAHER`).
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-venv python3-pip autoconf libtool pkg-config \
     zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
cd ~/SHAHER && ./scripts/build_android.sh      # SHAHER.apk + build_android.log
adb install -r SHAHER.apk
```
First build downloads several GB and takes 20–60 minutes.

## Configuration (buildozer.spec)
- `requirements = python3,kivy==2.3.1,sqlite3,pyjnius,android,arabic-reshaper==3.0.1,python-bidi==0.4.2,six`
  - `arabic-reshaper` and `python-bidi` are **pure-Python wheels** (checked); `arabic-reshaper` needs Python ≥ 3.10 (p4a's Python 3.11 is fine). python-bidi **must stay at 0.4.2** — newer releases are compiled (Rust) and will not build for Android.
  - `sqlite3` must be listed explicitly.
- Fonts are packaged because `ttf` is in `source.include_exts` (`assets/fonts/*.ttf`). Missing fonts = boxes instead of Arabic.
- `android.api = 33`, `minapi = 24`, `arm64-v8a`. Permission: `POST_NOTIFICATIONS` only.
- Reminders: `android.add_src = android/src` (Java), `android.gradle_dependencies = androidx.work:work-runtime:2.9.0`, `android.enable_androidx = True`. **New native dependency: AndroidX WorkManager.**
- Version 2.0.0.

## Why WorkManager
Buildozer cannot declare a boot `BroadcastReceiver` inside `<application>` (checked in buildozer 1.6.0 / p4a 2026.5.9). WorkManager keeps scheduled work across reboots by itself. Trade-off: timing is approximate (can be minutes late under Doze). The app also reschedules everything from the database at start and on resume (clock/timezone changes). Duplicate notifications are avoided with unique work names per commitment.

## What to test on a device (all currently UNVERIFIED)
1. Install; first launch shows onboarding; Arabic is joined and right-to-left (checklist in docs/ARABIC_VERIFICATION.md).
2. Typing Arabic in the title field (IME): text appears shaped, ✕ clears, saving keeps the exact text.
3. Android 13+: enabling a reminder asks for notification permission; denying shows the warning in the form and Settings; the "Allow notifications" and "Open app notification settings" buttons work.
4. Reminder 2 minutes ahead, app swiped away → notification arrives (note the delay). Tapping it opens SHAHER.
5. Edit the time → only one notification at the new time; complete/archive/delete → none.
6. Reboot with a pending reminder → still delivered.
7. Change the phone clock/timezone, reopen the app → reminders still match (resync on resume).
8. "Send a test notification" arrives in ~5 s; Arabic text in the notification looks right.
9. Battery saver / OEM restrictions: use "Battery optimisation exemption" and compare timing.
10. Dark theme "System" follows the phone setting; haptics (Settings → Experience) vibrate lightly.

## Troubleshooting
- `sdkmanager` licence error → keep `android.accept_sdk_license = True`.
- Gradle error mentioning `androidx.work` → check `enable_androidx` and the dependency line; open build_android.log.
- Java errors in `ReminderWorker/Scheduler` → they were never compiled by the author.
- `ModuleNotFoundError: _sqlite3` → `sqlite3` missing from requirements.
- `bidi`/`arabic_reshaper` import errors on device → the packages did not get bundled; confirm the requirement line and python-bidi 0.4.2.
- Boxes instead of Arabic → fonts not packaged.
- Reminders never show → Settings shows permission status; check system notification and battery settings.
