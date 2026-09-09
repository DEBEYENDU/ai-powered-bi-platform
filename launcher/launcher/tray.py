"""System tray icon (pystray). Degrades gracefully when unavailable."""

from __future__ import annotations

from collections.abc import Callable


def create_tray_icon(
    on_show: Callable[[], None],
    on_start: Callable[[], None],
    on_stop: Callable[[], None],
    on_quit: Callable[[], None],
):
    """Return a running-capable tray icon, or None if pystray is missing."""
    try:
        import pystray  # type: ignore
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    size = 64
    image = Image.new("RGB", (size, size), (30, 58, 95))
    draw = ImageDraw.Draw(image)
    draw.ellipse([14, 14, 50, 50], fill=(2, 136, 209))

    # pystray invokes callbacks as handler(icon, item); the lambdas adapt
    # zero-argument launcher callbacks to that signature.
    menu = pystray.Menu(
        pystray.MenuItem("Show", lambda _icon, _item: on_show(), default=True),
        pystray.MenuItem("Start project", lambda _icon, _item: on_start()),
        pystray.MenuItem("Stop project", lambda _icon, _item: on_stop()),
        pystray.MenuItem("Quit", lambda _icon, _item: on_quit()),
    )
    return pystray.Icon("bi-platform", image, "BI Platform Launcher", menu)
