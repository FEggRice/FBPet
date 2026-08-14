"""Game-like radial context menu: a dark neon wheel that springs open at the
cursor. The math (easing, geometry, hit-testing) lives in module-level
functions so it can be unit-tested without a display; RadialMenu renders them
on a transparent Toplevel and reports the chosen action through a callback."""
from __future__ import annotations

import math
import time
import tkinter as tk
from typing import Callable

# -- 动效参数 -----------------------------------------------------------------
OVERSHOOT = 1.438         # 弹簧过冲系数（ease-out-back 的 c1，参考 Rive 手感）
ENTRANCE_DUR = 0.32       # 单个按钮从圆心弹出的时长（秒）
ENTRANCE_STAGGER = 0.055  # 按钮逐个弹出的间隔（秒）
ROT_OFFSET = 0.55         # 整体入场旋转偏移（弧度），展开后回正
HOVER_DUR = 0.22          # 悬停放大动画时长（秒）
RELEASE_DUR = 0.14        # 离开按钮回落时长（秒）
HOVER_SCALE = 1.24        # 悬停放大倍数
HOVER_PUSH = 10           # 悬停沿半径外推像素
TICK_MS = 16              # 重绘间隔（约 60fps）

BUTTON_R = 30             # 按钮半径（像素）
RING_R = 92               # 按钮圆心到轮盘中心的距离（像素）
HIT_BAND = BUTTON_R * HOVER_SCALE + 12   # 命中圆环带的半宽（像素）
LABEL_PAD = 8             # 悬停标签距按钮外沿的间隙（像素）
LABEL_HALF = 44           # 悬停标签最大半宽预留（像素）
DIMMER_ALPHA = 0.12       # 全屏压暗遮罩的透明度

# -- 配色（暗色底 + 青色霓虹双层光晕） ----------------------------------------
COL_BTN = "#0b1a26"          # 常态按钮底色
COL_BTN_HOT = "#0e2436"      # 悬停按钮底色
COL_RING = "#22d3ee"         # 青色霓虹主环
COL_RING_HOT = "#8ff5ff"
COL_HALO_OUT = "#0e5a6e"     # 外层光晕（暗）
COL_HALO_OUT_HOT = "#2fb6d8"
COL_HALO_IN = "#15748f"      # 内层光晕
COL_HALO_IN_HOT = "#5fe0f2"
COL_ICON = "#6fe3f5"         # 常态图标色
COL_ICON_HOT = "#ffffff"     # 悬停图标变白
COL_LABEL_BG = "#08131d"
COL_LABEL_FG = "#dffbff"
COL_RAIL = "#0d1a26"         # 底层轨道环
COL_RAIL_IN = "#12303f"
COL_HUB = "#0a1722"          # 中心枢纽底色


def clamp(v: float, lo: float, hi: float) -> float:
    # 把 v 限制在 [lo, hi] 区间内
    return max(lo, min(hi, v))


def ease_out_cubic(t: float) -> float:
    # ease-out cubic：先快后慢，无过冲
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_out_back(t: float, s: float = OVERSHOOT) -> float:
    # ease-out-back：带回弹过冲的弹簧曲线，过冲量由 s 控制
    t = clamp(t, 0.0, 1.0)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def wheel_geometry(ring_r: float, count: int,
                   start_deg: float = -90.0) -> list[tuple[float, float]]:
    # 各按钮的目标圆心坐标（相对轮盘中心）：第 0 项朝正上方，顺时针排布
    out = []
    for i in range(count):
        ang = math.radians(start_deg + i * 360.0 / count)
        out.append((ring_r * math.cos(ang), ring_r * math.sin(ang)))
    return out


def clamp_center(x: float, y: float, extent: float,
                 sw: float, sh: float) -> tuple[float, float]:
    # 把轮盘圆心收进屏幕内：贴边时向内移，保证整个轮盘可见
    return (clamp(x, extent, sw - extent), clamp(y, extent, sh - extent))


def pick_item(dx: float, dy: float, ring_r: float, band: float,
              count: int, start_deg: float = -90.0) -> int | None:
    # 命中检测：指针落在 ring_r ± band 的圆环带内时按扇形角返回按钮下标
    d = math.hypot(dx, dy)
    if not (ring_r - band <= d <= ring_r + band):
        return None
    rel = (math.degrees(math.atan2(dy, dx)) - start_deg) % 360.0
    return int(rel // (360.0 / count)) % count


def _hex_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix_color(c1: str, c2: str, t: float) -> str:
    # 两色线性插值（canvas 不支持 alpha，用混色模拟淡入淡出）
    t = clamp(t, 0.0, 1.0)
    a, b = _hex_rgb(c1), _hex_rgb(c2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _rounded_points(x1: float, y1: float, x2: float, y2: float,
                    r: float, steps: int = 6) -> list[tuple[float, float]]:
    # 圆角矩形的多边形顶点序列（canvas 没有原生圆角矩形）
    pts: list[tuple[float, float]] = []

    def arc(cx: float, cy: float, a0: float, a1: float) -> None:
        for k in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * k / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    arc(x2 - r, y1 + r, -90, 0)
    arc(x2 - r, y2 - r, 0, 90)
    arc(x1 + r, y2 - r, 90, 180)
    arc(x1 + r, y1 + r, 180, 270)
    return pts


# -- 矢量图标（常态青色，悬停变白） -------------------------------------------

def _icon_settings(cv: tk.Canvas, x: float, y: float, r: float, color: str) -> None:
    # 齿轮：8 齿 + 齿圈 + 轴孔
    for k in range(8):
        a = math.radians(k * 45)
        cv.create_line(x + 0.78 * r * math.cos(a), y + 0.78 * r * math.sin(a),
                       x + 1.22 * r * math.cos(a), y + 1.22 * r * math.sin(a),
                       fill=color, width=3)
    cv.create_oval(x - r, y - r, x + r, y + r, outline=color, width=2)
    cv.create_oval(x - 0.36 * r, y - 0.36 * r, x + 0.36 * r, y + 0.36 * r, outline=color, width=2)


def _icon_hide(cv: tk.Canvas, x: float, y: float, r: float, color: str) -> None:
    # 隐藏到托盘：下箭头落入托盘条
    cv.create_line(x, y - 0.78 * r, x, y - 0.16 * r, fill=color, width=2.6)
    cv.create_line(x, y - 0.16 * r, x - 0.34 * r, y - 0.44 * r, fill=color, width=2.6)
    cv.create_line(x, y - 0.16 * r, x + 0.34 * r, y - 0.44 * r, fill=color, width=2.6)
    pts = _rounded_points(x - 0.58 * r, y + 0.02 * r, x + 0.58 * r, y + 0.5 * r, 0.12 * r)
    cv.create_polygon(pts, fill="", outline=color, width=2)


def _icon_quit(cv: tk.Canvas, x: float, y: float, r: float, color: str) -> None:
    # 退出：电源符号（缺口圆弧 + 竖线）
    cv.create_arc(x - 0.7 * r, y - 0.7 * r, x + 0.7 * r, y + 0.7 * r,
                  start=60, extent=240, style="arc", outline=color, width=2.6)
    cv.create_line(x, y - 0.64 * r, x, y - 0.06 * r, fill=color, width=2.6)


ICONS: dict[str, Callable] = {
    "settings": _icon_settings,
    "hide": _icon_hide,
    "quit": _icon_quit,
}


class RadialMenu:
    """径向轮盘菜单：在鼠标位置弹出，弹簧展开、悬停放大发光、点击选择。"""

    def __init__(self, root: tk.Tk, items: list[tuple[str, str]],
                 on_select: Callable[[str], None],
                 on_dismiss: Callable[[], None] | None = None,
                 transparent: str = "#ff00ff") -> None:
        # 初始化两个置顶无边框 Toplevel：全屏压暗遮罩（点击任意处关闭）+
        # 透明画布上的轮盘。两个窗口一次创建、反复复用
        self._root = root
        self._items = list(items)
        self._on_select = on_select
        self._on_dismiss = on_dismiss

        self._extent = int(RING_R + BUTTON_R * HOVER_SCALE + HOVER_PUSH
                           + LABEL_PAD + LABEL_HALF)
        size = self._extent * 2

        self._dim = tk.Toplevel(root)
        self._dim.overrideredirect(True)
        self._dim.attributes("-topmost", True)
        self._dim.attributes("-alpha", DIMMER_ALPHA)
        self._dim.configure(bg="#000000")
        for btn in ("<Button-1>", "<Button-3>"):
            self._dim.bind(btn, lambda e: self.dismiss())
        self._dim.withdraw()

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        try:
            self._win.attributes("-transparentcolor", transparent)
        except tk.TclError:
            pass
        self._win.configure(bg=transparent)
        self._cv = tk.Canvas(self._win, width=size, height=size,
                             bg=transparent, highlightthickness=0, bd=0)
        self._cv.pack()
        self._cv.bind("<Motion>", self._on_motion)
        self._cv.bind("<Button-1>", self._on_click)
        self._cv.bind("<Button-3>", lambda e: self.dismiss())
        self._win.bind("<Escape>", lambda e: self.dismiss())
        self._win.withdraw()

        self._open = False
        self._t0 = 0.0
        self._cx = self._cy = 0.0
        self._hovered: int | None = None
        self._prev_hovered: int | None = None
        self._hover_at = 0.0
        self._release_at = 0.0

    # -- 对外接口 ------------------------------------------------------------

    def is_open(self) -> bool:
        # 轮盘是否正在显示
        return self._open

    def popup(self, x_root: int, y_root: int) -> None:
        # 在屏幕坐标 (x_root, y_root) 处弹出轮盘（贴边自动内收）
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        cx, cy = clamp_center(x_root, y_root, float(self._extent), float(sw), float(sh))
        was_open = self._open
        self._open = True
        self._cx, self._cy = cx, cy
        self._win.geometry(f"{self._extent * 2}x{self._extent * 2}"
                           f"+{int(cx - self._extent)}+{int(cy - self._extent)}")
        self._dim.geometry(f"{sw}x{sh}+0+0")
        self._dim.deiconify()
        self._win.deiconify()
        self._win.lift()
        self._win.focus_force()
        self._t0 = time.perf_counter()
        self._hovered = self._prev_hovered = None
        self._hover_at = self._release_at = 0.0
        self._draw(0.0)
        if not was_open:  # 已在打开状态时沿用原有 tick 循环，避免重复调度
            self._win.after(TICK_MS, self._tick)

    def dismiss(self) -> None:
        # 关闭轮盘（不触发选择回调）
        if not self._open:
            return
        self._open = False
        self._win.withdraw()
        self._dim.withdraw()
        if self._on_dismiss:
            self._on_dismiss()

    # -- 动画循环 -------------------------------------------------------------

    def _tick(self) -> None:
        # 60fps 重绘：推进入场/悬停动画；窗口被销毁时静默退出
        if not self._open:
            return
        try:
            self._draw(time.perf_counter() - self._t0)
        except tk.TclError:
            return
        self._win.after(TICK_MS, self._tick)

    def _draw(self, elapsed: float) -> None:
        # 全量重绘一帧：轨道环 → 中心枢纽 → 各按钮（光环+底+图标）→ 悬停标签
        cv = self._cv
        cv.delete("all")
        cx = cy = float(self._extent)
        n = len(self._items)
        rot = ROT_OFFSET * (1 - ease_out_cubic(elapsed / ENTRANCE_DUR))  # 整体回正
        cv.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                       outline=COL_RAIL, width=10)
        cv.create_oval(cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R,
                       outline=COL_RAIL_IN, width=2)
        cv.create_oval(cx - 17, cy - 17, cx + 17, cy + 17,
                       fill=COL_HUB, outline="#1a4a5e", width=2)

        for i, ((tx, ty), (action, label)) in enumerate(zip(wheel_geometry(RING_R, n),
                                                            self._items)):
            p = clamp((elapsed - i * ENTRANCE_STAGGER) / ENTRANCE_DUR, 0.0, 1.0)
            if p <= 0:
                continue
            rad = ease_out_back(p)                      # 从圆心弹出的弹簧曲线
            ang = math.atan2(ty, tx) + rot              # 整体旋转偏移回正
            h = self._hover_progress(i, elapsed)        # 悬停进度（带回弹）
            x = cx + math.cos(ang) * (RING_R * rad + HOVER_PUSH * h)
            y = cy + math.sin(ang) * (RING_R * rad + HOVER_PUSH * h)
            r = BUTTON_R * rad * (1 + (HOVER_SCALE - 1) * h)
            self._draw_button(cv, action, x, y, r, h)
            if h > 0.02:
                self._draw_label(cv, label, x, y, r, h, ang)

    def _hover_progress(self, i: int, elapsed: float) -> float:
        # 当前悬停按钮用带回弹的弹簧曲线放大，刚离开的按钮平滑回落
        if i == self._hovered:
            return ease_out_back(clamp((elapsed - self._hover_at) / HOVER_DUR, 0.0, 1.0))
        if i == self._prev_hovered and self._release_at > 0:
            return 1 - ease_out_cubic(clamp((elapsed - self._release_at) / RELEASE_DUR, 0.0, 1.0))
        return 0.0

    def _draw_button(self, cv: tk.Canvas, action: str,
                     x: float, y: float, r: float, h: float) -> None:
        # 双层光晕 + 暗色圆底 + 矢量图标；悬停时发光变亮、图标变白
        cv.create_oval(x - r - 9, y - r - 9, x + r + 9, y + r + 9,
                       outline=mix_color(COL_HALO_OUT, COL_HALO_OUT_HOT, h),
                       width=3 + 2 * h)
        cv.create_oval(x - r - 4.5, y - r - 4.5, x + r + 4.5, y + r + 4.5,
                       outline=mix_color(COL_HALO_IN, COL_HALO_IN_HOT, h),
                       width=2 + 1.5 * h)
        cv.create_oval(x - r, y - r, x + r, y + r,
                       fill=mix_color(COL_BTN, COL_BTN_HOT, h),
                       outline=mix_color(COL_RING, COL_RING_HOT, h), width=2)
        ICONS.get(action, _icon_settings)(
            cv, x, y, r * 0.55, mix_color(COL_ICON, COL_ICON_HOT, h))

    def _draw_label(self, cv: tk.Canvas, label: str, x: float, y: float,
                    r: float, h: float, ang: float) -> None:
        # 悬停时浮现的中文标签：弹簧放大 + 混色淡入，贴按钮外沿、收在画布内
        font = ("Microsoft YaHei", max(7, int(9 + h)), "bold")
        probe = cv.create_text(x, y, text=label, font=font, fill=COL_LABEL_FG)
        x1, y1, x2, y2 = cv.bbox(probe)
        cv.delete(probe)
        w, hh = x2 - x1, y2 - y1
        padx, pady = 12, 6
        lx = x + math.cos(ang) * (r + LABEL_PAD + w / 2 + padx)
        ly = y + math.sin(ang) * (r + LABEL_PAD + hh / 2 + pady)
        half_w, half_h = w / 2 + padx, hh / 2 + pady
        size = float(self._extent * 2)
        lx = clamp(lx, half_w + 2, size - half_w - 2)
        ly = clamp(ly, half_h + 2, size - half_h - 2)
        pts = _rounded_points(lx - half_w, ly - half_h, lx + half_w, ly + half_h, 11)
        cv.create_polygon(pts, fill=COL_LABEL_BG,
                          outline=mix_color(COL_LABEL_BG, COL_RING, h), width=1.5)
        cv.create_text(lx, ly, text=label, font=font,
                       fill=mix_color(COL_LABEL_BG, COL_LABEL_FG, h))

    # -- 输入 -----------------------------------------------------------------

    def _on_motion(self, e) -> None:
        # 鼠标移动：命中检测更新悬停项（悬停带动画）
        if not self._open:
            return
        self._set_hover(pick_item(e.x_root - self._cx, e.y_root - self._cy,
                                  RING_R, HIT_BAND, len(self._items)))

    def _on_click(self, e) -> None:
        # 左键：点中按钮触发选择，点空白处仅关闭
        if not self._open:
            return
        idx = pick_item(e.x_root - self._cx, e.y_root - self._cy,
                        RING_R, HIT_BAND, len(self._items))
        if idx is not None:
            action = self._items[idx][0]
            self.dismiss()
            self._on_select(action)
        else:
            self.dismiss()

    def _set_hover(self, idx: int | None) -> None:
        # 悬停项切换：记录旧项回落 / 新项放大的起始时刻
        if idx == self._hovered:
            return
        now = time.perf_counter() - self._t0
        if self._hovered is not None:
            self._prev_hovered = self._hovered
            self._release_at = now
        self._hovered = idx
        if idx is not None:
            self._hover_at = now
        self._cv.config(cursor="hand2" if idx is not None else "")
