#!/bin/bash
# Build a standalone macOS app bundle for BOZO Ball and drop it on the Desktop.
# Re-run this any time the source changes.
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="BOZO_BALL"
DESKTOP="$HOME/Desktop"
TARGET="$DESKTOP/$APP_NAME.app"
VENV_PY=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# Any older / renamed builds we want to sweep off the Desktop on every run.
OLD_APPS=("KellyBall.app" "BOZO_BALL.app" "BozoBall.app")

if [ ! -x "$VENV_PY" ]; then
    echo "error: .venv/bin/python not found — create the venv first" >&2
    exit 1
fi

# Remove old executables from the Desktop before building.
for old in "${OLD_APPS[@]}"; do
    if [ -e "$DESKTOP/$old" ]; then
        echo "Removing old $DESKTOP/$old ..."
        rm -rf "$DESKTOP/$old"
    fi
done

# Install pyinstaller into the venv if missing.
if ! "$VENV_PIP" show pyinstaller >/dev/null 2>&1; then
    echo "Installing pyinstaller into .venv ..."
    "$VENV_PIP" install --quiet pyinstaller
fi

# Wipe stale build artefacts so we never ship a half-rebuilt bundle.
rm -rf build dist "$APP_NAME.spec"

# If an intro image or audio file exists, bundle it so the .app can find it at runtime.
# Also scans ~/Desktop/BOZO_RESOURCES (the external resource folder the app reads).
# Dedupes by case-folded basename — macOS's case-insensitive filesystem will
# match "bozo.mp3" to "BOZO.mp3", and PyInstaller can't bundle both.
ASSET_NAMES=(intro.png intro.gif intro.mp3 intro.m4a intro.wav splash.mp3 splash.m4a splash.wav bozo.mp3 BOZO.mp3 bozo.m4a bozo.wav background.mp3 Background.mp3 background.m4a background.wav BOZO_IMAGE.png ANIMATION.mp3)
ASSET_DIRS=("." "$HOME/Desktop/BOZO_RESOURCES")
INTRO_FLAGS=()
SEEN_ASSETS=""  # macOS default bash 3.2 has no assoc arrays; use a delimited string
for d in "${ASSET_DIRS[@]}"; do
    for f in "${ASSET_NAMES[@]}"; do
        if [ -f "$d/$f" ]; then
            key=$(echo "$f" | tr '[:upper:]' '[:lower:]')
            case "$SEEN_ASSETS" in
                *"|$key|"*) ;;
                *)
                    SEEN_ASSETS="$SEEN_ASSETS|$key|"
                    INTRO_FLAGS+=(--add-data "$d/$f:.")
                    echo "Bundling asset: $d/$f"
                    ;;
            esac
        fi
    done
done

echo "Building $APP_NAME.app ..."
"$VENV_PY" -m PyInstaller \
    --name "$APP_NAME" \
    --windowed \
    --noconfirm \
    --clean \
    ${INTRO_FLAGS[@]+"${INTRO_FLAGS[@]}"} \
    --collect-submodules kelly_ball \
    bozo_ball.py >/dev/null

if [ ! -d "dist/$APP_NAME.app" ]; then
    echo "error: PyInstaller did not produce dist/$APP_NAME.app" >&2
    exit 1
fi

mv "dist/$APP_NAME.app" "$TARGET"

# Tidy up — leave the source folder clean for the next iteration.
rm -rf build dist "$APP_NAME.spec"

# Quit any existing instance so the freshly built app boots cleanly,
# then launch the new one so the user doesn't have to open it manually.
osascript -e "tell application \"$APP_NAME\" to quit" >/dev/null 2>&1 || true
sleep 0.2
open "$TARGET"

echo "Done. $TARGET (launched)"
