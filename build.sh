#!/bin/bash
# Build a standalone macOS app bundle for BOZO Ball (3D / pywebview build)
# and drop it on the Desktop. Re-run any time the source changes.
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="BOZO_BALL"
DESKTOP="$HOME/Desktop"
TARGET="$DESKTOP/$APP_NAME.app"
VENV_PY=".venv/bin/python"

# Older / renamed builds to sweep off the Desktop on every run.
OLD_APPS=("KellyBall.app" "BOZO_BALL.app" "BozoBall.app")

if [ ! -x "$VENV_PY" ]; then
    echo "error: .venv/bin/python not found — create the venv first" >&2
    echo "       (e.g. 'uv venv .venv && uv pip install -r requirements.txt')" >&2
    exit 1
fi

for old in "${OLD_APPS[@]}"; do
    [ -e "$DESKTOP/$old" ] && { echo "Removing old $DESKTOP/$old ..."; rm -rf "$DESKTOP/$old"; }
done

# Ensure build deps are present.
"$VENV_PY" -m pip show pyinstaller >/dev/null 2>&1 || \
    "$VENV_PY" -m pip install --quiet pyinstaller

# Wipe stale artefacts so we never ship a half-rebuilt bundle.
rm -rf build dist "$APP_NAME.spec"

echo "Building $APP_NAME.app ..."
"$VENV_PY" -m PyInstaller \
    --name "$APP_NAME" \
    --windowed \
    --noconfirm \
    --clean \
    --add-data "kelly_ball/web:kelly_ball/web" \
    --collect-submodules kelly_ball \
    --collect-all webview \
    bozo_ball.py >/dev/null

[ -d "dist/$APP_NAME.app" ] || { echo "error: PyInstaller produced no app bundle" >&2; exit 1; }

mv "dist/$APP_NAME.app" "$TARGET"
rm -rf build dist "$APP_NAME.spec"

# Relaunch the fresh build.
osascript -e "tell application \"$APP_NAME\" to quit" >/dev/null 2>&1 || true
sleep 0.2
open "$TARGET"

echo "Done. $TARGET (launched)"
