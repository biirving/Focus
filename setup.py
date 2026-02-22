"""py2app build configuration for Focus OS."""

import sys
import zlib

# ── Workaround for py2app bug with builtin zlib ──
# On uv-managed Python, zlib is a builtin module (no __file__).
# py2app unconditionally does: self.copy_file(zlib.__file__, ...)
# which crashes. On modern macOS the system libz is in the dyld
# shared cache and can't be copied either. Since zlib is statically
# linked into the interpreter, we monkey-patch py2app to skip the copy.
if not hasattr(zlib, "__file__"):
    import py2app.build_app

    _orig_build_executable = py2app.build_app.py2app.build_executable

    def _patched_build_executable(self, *args, **kwargs):
        # Temporarily give zlib a fake __file__ that we intercept
        zlib.__file__ = "__builtin_zlib__"
        _orig_copy_file = self.copy_file

        def _safe_copy_file(src, dst, **kw):
            if src == "__builtin_zlib__":
                return (dst, 0)  # skip — zlib is builtin
            return _orig_copy_file(src, dst, **kw)

        self.copy_file = _safe_copy_file
        try:
            return _orig_build_executable(self, *args, **kwargs)
        finally:
            self.copy_file = _orig_copy_file
            del zlib.__file__

    py2app.build_app.py2app.build_executable = _patched_build_executable

from setuptools import setup

APP = ["focus/gui.py"]
DATA_FILES = [
    ("", ["config.yaml", "prompt.md"]),
    ("focus", ["focus/banner.swift"]),
]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,  # Replace with .icns path if you have one
    "plist": {
        "CFBundleName": "Focus",
        "CFBundleDisplayName": "Focus OS",
        "CFBundleIdentifier": "com.focusos.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Menu bar only — no Dock icon
    },
    "packages": ["focus", "rumps", "webview", "yaml", "dotenv", "anthropic"],
}

setup(
    app=APP,
    name="Focus",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
