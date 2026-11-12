#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$project_dir/nas/android"
# Use Android Studio's installed JDK/SDK or explicitly supplied JAVA_HOME/ANDROID_HOME.
test -n "${JAVA_HOME:-}" || { echo 'Set JAVA_HOME to JDK 17 or 21.'; exit 1; }
test -n "${ANDROID_HOME:-}" || { echo 'Set ANDROID_HOME to Android SDK with platform 36 and build-tools 36.0.0.'; exit 1; }
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > local.properties
bash ../../android/gradlew -p "$PWD" --no-daemon --console=plain assembleDebug
mkdir -p "$project_dir/output/nas"
cp app/build/outputs/apk/debug/app-debug.apk "$project_dir/output/nas/Planwise-NAS-0.3.0-preview.apk"
"$ANDROID_HOME/build-tools/36.0.0/apksigner" verify --verbose "$project_dir/output/nas/Planwise-NAS-0.3.0-preview.apk"
"$ANDROID_HOME/build-tools/36.0.0/zipalign" -c -P 16 4 "$project_dir/output/nas/Planwise-NAS-0.3.0-preview.apk"
