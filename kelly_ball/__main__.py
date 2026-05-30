"""`python -m kelly_ball` entry point — launches the 3D webview app.

The Tkinter UI is replaced by a Three.js front-end hosted in a native OS
webview (WKWebView / WebView2 / GTK-WebKit) via pywebview. Game logic lives
in :class:`kelly_ball.core.GameController`, bridged through
:class:`kelly_ball.api.Api`.
"""
from __future__ import annotations

import mimetypes
import os
import sys
from pathlib import Path

import webview

from .api import Api


def _register_mime_types() -> None:
    """Force correct JS/JSON MIME types.

    pywebview serves the bundled ``web/`` files through bottle, whose
    ``static_file`` trusts ``mimetypes.guess_type``. On some macOS setups the
    system registry maps ``.js`` to ``text/plain``, and WKWebView then refuses
    to run it as an ES module ("requires a type attribute"). Registering the
    types here makes the front-end load regardless of the host's registry.
    """
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("application/json", ".json")


def _web_dir() -> Path:
    """Locate the bundled ``web/`` assets in dev and inside PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "kelly_ball" / "web"
    return Path(__file__).resolve().parent / "web"


def main() -> None:
    _register_mime_types()
    index = _web_dir() / "index.html"
    api = Api()
    window = webview.create_window(
        "BOZO Ball",
        url=str(index),
        js_api=api,
        width=1180,
        height=760,
        min_size=(900, 620),
        background_color="#0f1115",
    )

    # Force-exit the instant the user requests a close. Without this, closing the
    # window beachballs and the process never exits (macOS / WKWebView): the
    # native teardown (windowWillClose_) tears the webview down while the WebGL
    # render loop is still running, wedging the main thread.
    #
    # `closing` fires synchronously on the main thread (for both the red button
    # and Cmd-Q) *before* that teardown, so os._exit here kills the process
    # cleanly before the hang can happen. (Doing the same on `closed` is too late
    # — it fires after the wedge; and calling evaluate_js from `closing` would
    # itself deadlock the main thread.) Safe to exit hard: settings/roster are
    # persisted synchronously on every change, not at exit.
    window.events.closing += lambda: os._exit(0)

    # http_server=True serves over http:// instead of file://, required for
    # ES modules + import maps to load in the native webview (file:// trips
    # module CORS). gui=None lets pywebview pick the platform backend.
    webview.start(http_server=True)


if __name__ == "__main__":
    main()
