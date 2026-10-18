#!/usr/bin/env bash
# Build a debug APK. Run on Linux or WSL2 (Ubuntu), NOT in plain Windows.
set -euo pipefail
cd "$(dirname "$0")/.."

fail() { echo "ERROR: $1" >&2; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "Android builds need Linux or WSL2 (see docs/ANDROID_BUILD.md)."
command -v python3 >/dev/null || fail "python3 is missing."
command -v java    >/dev/null || fail "Java JDK 17 is missing (sudo apt install openjdk-17-jdk)."
command -v git     >/dev/null || fail "git is missing (sudo apt install git)."

python3 -m venv .venv-android
# shellcheck disable=SC1091
source .venv-android/bin/activate
pip install --upgrade pip
pip install buildozer "cython<3.1"

buildozer -v android debug 2>&1 | tee build_android.log

APK=$(ls -t bin/*.apk 2>/dev/null | head -n1 || true)
[ -n "$APK" ] && [ -s "$APK" ] || fail "No APK was produced. See build_android.log."
cp "$APK" SHAHER.apk
echo "Built: $(pwd)/SHAHER.apk ($(du -h SHAHER.apk | cut -f1)). Compiled only - NOT tested on a device."
