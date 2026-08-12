"""System tray icon (pystray). Callbacks run on pystray's thread — the app
marshals them to the UI thread via a queue."""
from __future__ import annotations

import threading

import pystray
from PIL import Image, ImageDraw


class TrayIcon:
    def __init__(self, on_show, on_settings, on_quit) -> None:
        self._icon = pystray.Icon(
            "fb_pet",
            self._make_icon(),
            "FB Pet",
            pystray.Menu(
                pystray.MenuItem("显示宠物", lambda _i, _it: on_show()),
                pystray.MenuItem("设置", lambda _i, _it: on_settings()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", lambda _i, _it: on_quit()),
            ),
        )
        self._thread: threading.Thread | None = None

    @staticmethod
    def _make_icon() -> Image.Image:
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, 30, 30], fill=(255, 165, 0), outline=(120, 80, 0), width=2)
        return img

    def start(self) -> None:
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def show(self) -> None:
        self._icon.visible = True

    def hide(self) -> None:
        self._icon.visible = False

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass
