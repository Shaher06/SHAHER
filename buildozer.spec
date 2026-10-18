[app]
title = SHAHER
package.name = shaher
package.domain = org.shaher
version = 2.0.0

source.dir = .
source.include_exts = py,png,ttf,txt
source.exclude_dirs = tests,docs,scripts,bin,.venv,venv,.git,__pycache__,.buildozer,.pytest_cache
source.exclude_patterns = *.db,*.log,*.zip

# sqlite3 and android are needed explicitly; pyjnius is used by the reminder backend.
requirements = python3,kivy==2.3.1,sqlite3,pyjnius,android,arabic-reshaper==3.0.1,python-bidi==0.4.2,six

icon.filename = %(source.dir)s/assets/icons/icon.png
orientation = portrait
fullscreen = 0

# POST_NOTIFICATIONS is requested at runtime on Android 13+ (needed for reminders).
android.permissions = android.permission.POST_NOTIFICATIONS

# API 33 is python-for-android's recommended target. Not yet verified by a real build here.
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

# Reminders: Java classes + AndroidX WorkManager (survives reboots).
android.add_src = android/src
android.enable_androidx = True
android.gradle_dependencies = androidx.work:work-runtime:2.9.0

[buildozer]
log_level = 2
warn_on_root = 1
