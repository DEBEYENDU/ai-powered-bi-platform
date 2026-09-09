"""Build script: packages the launcher as BI Platform Launcher.exe.

Usage (from the launcher/ directory):
    pip install pyinstaller
    python build_exe.py

Output: launcher/dist/BI Platform Launcher.exe (single file, windowed).
Double-clicking it starts the GUI; pass --root if the exe lives outside
the project checkout.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

APP_NAME = "BI Platform Launcher"
ENTRY = Path(__file__).resolve().parent / "main.py"


def main() -> int:
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller")
        return 2

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        # Bundle CustomTkinter theme assets + Pillow plugins explicitly.
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "pystray",
        str(ENTRY),
    ]
    print("$", " ".join(command))
    completed = subprocess.run(command, cwd=str(ENTRY.parent), check=False)
    if completed.returncode != 0:
        print("PyInstaller build failed.")
        return 1
    exe = ENTRY.parent / "dist" / f"{APP_NAME}.exe"
    if exe.is_file():
        print(f"Built: {exe} ({exe.stat().st_size // 1024 // 1024} MB)")
        return 0
    # Non-Windows fallback name for CI smoke builds.
    fallback = ENTRY.parent / "dist" / APP_NAME
    if fallback.is_file():
        print(f"Built: {fallback}")
        return 0
    print("Build finished but no executable found in dist/.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
