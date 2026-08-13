"""System tray icon (pystray). Callbacks run on pystray's thread — the app
marshals them to the UI thread via a queue."""
from __future__ import annotations

import threading

import pystray
from PIL import Image, ImageDraw


class TrayIcon:
    # 系统托盘图标（pystray）：右键菜单 显示宠物 / 设置 / 退出。
    # 回调运行在 pystray 自己的线程，app 侧通过队列转回 UI 线程

    def __init__(self, on_show, on_settings, on_quit) -> None:
        # 初始化：创建托盘图标、图标图片和右键菜单，三个回调分别对应菜单项
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
        # 程序化画一个 32×32 的橙色圆形作为托盘图标
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, 30, 30], fill=(255, 165, 0), outline=(120, 80, 0), width=2)
        return img

    def start(self) -> None:
        # 在独立守护线程里启动托盘图标的事件循环
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def show(self) -> None:
        # 让托盘图标可见
        self._icon.visible = True

    def hide(self) -> None:
        # 隐藏托盘图标
        self._icon.visible = False

    def stop(self) -> None:
        # 停止托盘图标（退出时调用，容错处理）
        try:
            self._icon.stop()
        except Exception:
            pass
