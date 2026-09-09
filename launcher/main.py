"""BI Platform Launcher entry point.

Usage:
    python main.py [--root <project-root>] [--no-splash]

Double-clicking the packaged BI Platform Launcher.exe does the same.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import traceback
from pathlib import Path


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="BI Platform Launcher")
    parser.add_argument("--root", default="", help="Project root directory")
    parser.add_argument("--no-splash", action="store_true", help="Skip splash screen")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    launcher_package = Path(__file__).resolve().parent
    if str(launcher_package) not in sys.path:
        sys.path.insert(0, str(launcher_package))

    try:
        import customtkinter as ctk
    except ImportError:
        print("ERROR: customtkinter is not installed. Run: pip install -r requirements.txt")
        return 2

    from launcher.paths import ProjectPaths
    from launcher.ui_app import LauncherApp, show_splash

    root = Path(args.root).resolve() if args.root else None
    paths = ProjectPaths(root)
    if not paths.has_backend() or not paths.has_frontend():
        print(f"ERROR: not a BI Platform checkout: {paths.root}")
        print("Pass --root <project-root> or run from inside the project.")
        return 2

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # A hidden root owns the splash; the app creates the real window.
    hidden = ctk.CTk()
    hidden.withdraw()
    splash = None
    if not args.no_splash:
        try:
            splash, status = show_splash(hidden)
            status.configure(text="Loading launcher...")
            hidden.update()
        except Exception:
            splash = None

    try:
        app = LauncherApp(paths.root)
    except Exception:
        traceback.print_exc()
        with contextlib.suppress(Exception):
            if splash is not None:
                splash.destroy()
        with contextlib.suppress(Exception):
            hidden.destroy()
        return 1

    with contextlib.suppress(Exception):
        if splash is not None:
            splash.destroy()
    with contextlib.suppress(Exception):
        hidden.destroy()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
