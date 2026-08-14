"""tkinter views: PetWindow (transparent topmost pet), BubbleWindow (click-through
message), SettingsDialog. Pure view layer — no business logic, all effects via callbacks."""
from __future__ import annotations

import ctypes
import math
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import ImageTk

from .frames import load_frames
from .radial import button_centers, hit_test, wheel_half_size


class PetWindow:
    # 宠物主窗口：透明无边框、置顶、显示精灵帧；支持拖动、点击、右键菜单

    def __init__(self, cfg, on_click, on_context) -> None:
        # 初始化：创建透明置顶无边框 tk 窗口，加载帧定尺寸，放屏幕右下角，
        # 绑定鼠标事件，建右键菜单
        self.cfg = cfg
        self.on_click = on_click
        self.on_context = on_context

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.key = cfg.get("window", "transparentColor", default="#ff00ff")
        try:
            self.root.attributes("-transparentcolor", self.key)
        except tk.TclError:
            pass
        self.root.configure(bg=self.key)

        self.frames, display = self._load_frames()
        w, h = display
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 20}")  # bottom-right

        self._label = tk.Label(self.root, bg=self.key, cursor="hand2")
        self._label.pack()
        self._label.bind("<ButtonPress-1>", self._on_down)
        self._label.bind("<B1-Motion>", self._on_move)
        self._label.bind("<ButtonRelease-1>", self._on_up)
        self._label.bind("<Button-3>", self._on_right)

        self._drag_start = None
        self._moved = False
        # 环形转轮右键菜单：设置 / 隐藏到托盘 / 退出（顺序即圆周顺时针排布，从正上方开始）
        self._radial = RadialMenu(
            self.root,
            self.key,
            actions=[
                ("设置", "⚙", "settings"),
                ("隐藏到托盘", "▬", "hide"),
                ("退出", "✕", "quit"),
            ],
            on_action=self.on_context,
        )

    # -- view ----------------------------------------------------------------

    def show_frame(self, state: str, index: int) -> None:
        # 在窗口上显示某状态的某一帧（下标合法时更新图片）
        imgs = self.frames.get(state)
        if imgs and index < len(imgs):
            self._label.config(image=imgs[index])

    def reload_frames(self) -> None:
        # 重新读精灵表/图片并原位调整窗口尺寸（设置保存后调用）
        self.frames, display = self._load_frames()
        x, y = self.root.winfo_x(), self.root.winfo_y()
        w, h = display
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def hide(self) -> None:
        # 隐藏窗口（隐藏到托盘时用）
        self.root.withdraw()

    def show(self) -> None:
        # 重新显示窗口（从托盘恢复时用）
        self.root.deiconify()

    def position(self) -> tuple[int, int, int, int]:
        # 返回窗口几何：x, y, 宽, 高（供气泡定位用）
        return (self.root.winfo_x(), self.root.winfo_y(),
                self.root.winfo_width(), self.root.winfo_height())

    def frame_count(self, state: str) -> int:
        # 返回某状态的帧数（用于建 animator）
        return len(self.frames.get(state) or [])

    def _load_frames(self) -> tuple[dict[str, list], tuple[int, int]]:
        # 调 load_frames 解析各状态帧，包装成 ImageTk.PhotoImage，返回 (帧字典, 尺寸)。
        # box = 窗口基准尺寸 × 用户缩放倍数（scale）
        sheet = self.cfg.sprite_sheet
        path = self.cfg.resolve(sheet.get("path", "pet.png"))
        scale = self.cfg.get("window", "scale", default=1.0)
        box = (
            int(self.cfg.get("window", "width", default=128) * scale),
            int(self.cfg.get("window", "height", default=128) * scale),
        )
        frames, size = load_frames(path, self.cfg.base_dir, sheet, self.cfg.animations, box)
        return {name: [ImageTk.PhotoImage(im, master=self.root) for im in imgs] for name, imgs in frames.items()}, size

    # -- input ---------------------------------------------------------------

    def _on_down(self, e) -> None:
        # 鼠标按下：记录拖拽起点、清除移动标记
        self._drag_start = (e.x_root, e.y_root)
        self._moved = False

    def _on_move(self, e) -> None:
        # 鼠标拖动：超过 5px 判定为拖动，随鼠标移动窗口位置
        if not self._drag_start:
            return
        dx = e.x_root - self._drag_start[0]
        dy = e.y_root - self._drag_start[1]
        if abs(dx) + abs(dy) > 5:
            self._moved = True
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"+{x + dx}+{y + dy}")
        self._drag_start = (e.x_root, e.y_root)

    def _on_up(self, e) -> None:
        # 鼠标释放：若没有拖动则视为一次点击，触发 on_click
        if self._drag_start and not self._moved:
            self.on_click()
        self._drag_start = None

    def _on_right(self, e) -> None:
        # 右键：在鼠标处弹出环形转轮菜单
        self._radial.show(e.x_root, e.y_root)


class BubbleWindow:
    """Click-through topmost bubble shown next to the pet. Uses FindWindow by a
    unique title to grab its HWND and set WS_EX_TRANSPARENT so clicks pass through."""

    _TITLE = "_fb_pet_bubble_"

    def __init__(self, root, key: str) -> None:
        # 初始化：创建透明置顶无边框 Toplevel，带文本标签，默认隐藏，并设置点击穿透
        self.root = root
        self._win = tk.Toplevel(root)
        self._win.title(self._TITLE)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        try:
            self._win.attributes("-transparentcolor", key)
        except tk.TclError:
            pass
        self._win.configure(bg=key)
        self._label = tk.Label(
            self._win,
            text="",
            bg="#1a1a1a",
            fg="#ffffff",
            font=("Microsoft YaHei", 11),
            wraplength=280,
            justify="left",
            padx=14,
            pady=10,
        )
        self._label.pack()
        self._win.withdraw()
        self._make_click_through()

    def show(self, text: str, pet_rect) -> None:
        # 在宠物旁边显示气泡文字：先算自身尺寸再定位（自动避让屏幕左/右边缘）
        self._label.config(text=text)
        self._win.update_idletasks()
        w = self._label.winfo_reqwidth()
        h = self._label.winfo_reqheight()
        px, py, pw, ph = pet_rect
        x = px - w - 10
        y = py + ph // 2 - h // 2
        sw = self.root.winfo_screenwidth()
        if x < 0:
            x = px + pw + 10
        if x + w > sw:
            x = sw - w - 5
        self._win.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self._win.deiconify()

    def hide(self) -> None:
        # 隐藏气泡
        self._win.withdraw()

    def _make_click_through(self) -> None:
        # 通过窗口标题 FindWindow 拿 HWND，加 WS_EX_TRANSPARENT 样式让点击穿透
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, self._TITLE)
            if not hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x20
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if hasattr(user32, "SetWindowLongPtrW"):
                user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT)
            else:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT)
        except Exception:
            pass


def _ease_out_back(t: float) -> float:
    # 缓出带回弹：t∈[0,1] → 越过 1 再落回（产生弹簧挤压的过冲）
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


class RadialMenu:
    # 右键环形转轮菜单：透明置顶无边框 Toplevel + Canvas，游戏感动效。
    # 入场：按钮从圆心逐个带弹跳出弹到圆周，同时整体旋转展开（弹簧）；
    # 悬停：目标按钮弹性放大、向外推出、亮起霓虹辉光，中文标签此时才浮现；
    # 常态只显示图标+暗色环。左键触发动作，点空白/右键/Escape 关闭

    ICON_FONT = ("Segoe UI Symbol", 26)
    LABEL_FONT = ("Microsoft YaHei", 11)
    RING_RADIUS = 88       # 圆心到按钮中心的距离
    BUTTON_RADIUS = 34     # 普通按钮半径
    HOVER_SCALE = 1.35     # 悬停放大倍数
    HOVER_PUSH = 35        # 悬停沿半径向外推出的系数（乘过冲量）
    HIT_RADIUS = 40        # 命中判定半径
    MARGIN = 6
    LABEL_PAD = 22         # 悬停按钮下方给标签留的空间
    SPIN_START = -30.0     # 入场旋转起点（度），弹簧回落 0 → 展开感
    FRAMES = 16            # 单个按钮入场帧数
    STAGGER = 5            # 相邻按钮入场间隔帧
    _TICK_MS = 33          # 动画帧率 ≈30fps

    # 霓虹配色
    BUTTON_BG = "#15181e"
    OUTLINE_NORMAL = "#334155"
    OUTLINE_HOVER = "#9ff0ff"
    GLOW_FAR = "#123a4d"
    GLOW_NEAR = "#1f6f94"
    ICON_NORMAL = "#94a3b8"
    ICON_HOVER = "#ffffff"
    LABEL_FILL = "#e6f7ff"
    RING_FILL = "#223147"

    def __init__(self, root, key: str, actions, on_action) -> None:
        # 初始化：actions 形如 [(标签, 图标, action), ...]，依次对应圆周各角度；
        # 建透明置顶无边框 Toplevel 和 Canvas，绑定移动/左键/右键/Escape，默认隐藏
        self._root = root
        self._on_action = on_action
        self._actions = actions
        self._hovered: int | None = None

        half = wheel_half_size(self.RING_RADIUS, self.BUTTON_RADIUS * self.HOVER_SCALE
                               + self.LABEL_PAD, self.MARGIN)
        self._size = int(half * 2)
        self._center = (half, half)
        n = len(actions)
        self._s = [1.0] * n      # 每按钮当前缩放（弹簧位置）
        self._sv = [0.0] * n     # 每按钮缩放速度
        self._frame = 0          # 入场动画帧计数
        self._rot = 0.0          # 整体旋转偏移（弹簧位置）
        self._rv = 0.0           # 旋转速度

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        try:
            self._win.attributes("-transparentcolor", key)
        except tk.TclError:
            pass
        self._win.configure(bg=key)
        self._win.geometry(f"{self._size}x{self._size}")

        self._canvas = tk.Canvas(self._win, width=self._size, height=self._size,
                                 bg=key, highlightthickness=0)
        self._canvas.pack()
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Button-3>", lambda e: self.hide())
        self._canvas.bind("<Escape>", lambda e: self.hide())
        self._win.withdraw()

    # -- 公共接口 -------------------------------------------------------------

    def show(self, x_root: int, y_root: int) -> None:
        # 把轮盘中心对准鼠标（夹在屏幕内），重置动画状态、显示并抓取鼠标，启动动画循环
        x = x_root - int(self._center[0])
        y = y_root - int(self._center[1])
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(0, min(x, sw - self._size))
        y = max(0, min(y, sh - self._size))
        self._win.geometry(f"+{x}+{y}")
        self._hovered = None
        self._frame = 0
        self._rot, self._rv = self.SPIN_START, 0.0
        for i in range(len(self._actions)):
            self._s[i], self._sv[i] = 1.0, 0.0
        self._win.deiconify()
        self._win.lift()
        self._win.grab_set()
        self._canvas.focus_set()
        self._tick()

    def hide(self) -> None:
        # 释放鼠标抓取并隐藏转轮（容错处理）
        try:
            self._win.grab_release()
        except tk.TclError:
            pass
        self._hovered = None
        self._win.withdraw()

    # -- 动画循环 -------------------------------------------------------------

    def _tick(self) -> None:
        # 动画心跳：推进入场帧、旋转弹簧、各按钮悬停缩放弹簧，重绘；窗口可见则续跑
        self._frame += 1
        self._rot, self._rv = self._spring(self._rot, self._rv, 0.0)
        for i in range(len(self._actions)):
            target = self.HOVER_SCALE if i == self._hovered else 1.0
            self._s[i], self._sv[i] = self._spring(self._s[i], self._sv[i], target)
        self._redraw()
        if self._win.state() == "normal":
            self._win.after(self._TICK_MS, self._tick)

    @staticmethod
    def _spring(pos: float, vel: float, target: float) -> tuple[float, float]:
        # 欠阻尼弹簧：过冲一次后回落，产生弹性手感（每帧 33ms 的时间步）
        accel = (target - pos) * 0.16
        vel = vel * 0.70 + accel
        return pos + vel, vel

    # -- 布局 -----------------------------------------------------------------

    def _base_centers(self) -> list[tuple[float, float]]:
        # 完全展开后各按钮圆心（第一个在正上方，顺时针）
        return button_centers(len(self._actions), self._center, self.RING_RADIUS)

    def _current_centers(self) -> list[tuple[float, float]]:
        # 当前帧各按钮圆心：入场阶段从圆心沿各自方向弹出（ease_out_back 带回弹），
        # 角度叠加残余旋转量，实现「逐个弹出 + 整体旋转展开」；悬停时沿半径外推
        cx = cy = self._center[0]
        n = len(self._actions)
        step = 360.0 / n
        out = []
        for i in range(n):
            t = max(0.0, min(1.0, (self._frame - i * self.STAGGER) / self.FRAMES))
            r = _ease_out_back(t) * self.RING_RADIUS
            ang = math.radians(90 + i * step + self._rot * (1 - t))
            bx = cx + r * math.cos(ang)
            by = cy - r * math.sin(ang)
            if self._s[i] > 1.0:
                dx, dy = bx - cx, by - cy
                d = math.hypot(dx, dy) or 1.0
                push = (self._s[i] - 1.0) * self.HOVER_PUSH
                bx += dx / d * push
                by += dy / d * push
            out.append((bx, by))
        return out

    # -- 输入 -----------------------------------------------------------------

    def _on_motion(self, e) -> None:
        # 鼠标移动：按当前帧按钮位置命中测试，悬停目标变化由弹簧动画平滑过渡
        idx = hit_test(self._current_centers(), e.x, e.y, self.HIT_RADIUS)
        if idx != self._hovered:
            self._hovered = idx

    def _on_click(self, e) -> None:
        # 左键：命中按钮则先关闭转轮（释放 grab）再执行动作，否则仅关闭
        idx = hit_test(self._current_centers(), e.x, e.y, self.HIT_RADIUS)
        if idx is not None:
            action = self._actions[idx][2]
            self.hide()
            self._on_action(action)
        else:
            self.hide()

    # -- 绘制 -----------------------------------------------------------------

    def _redraw(self) -> None:
        # 全量重绘：外圈淡环 → 每按钮（辉光、暗底圆、图标）→ 悬停按钮出中文标签
        c = self._canvas
        c.delete("all")
        cx = cy = self._center[0]

        c.create_oval(cx - self.RING_RADIUS, cy - self.RING_RADIUS,
                      cx + self.RING_RADIUS, cy + self.RING_RADIUS,
                      outline=self.RING_FILL, width=1)

        centers = self._current_centers()
        for i, (label, icon, _action) in enumerate(self._actions):
            bx, by = centers[i]
            br = self.BUTTON_RADIUS * self._s[i]
            hovered = i == self._hovered

            if hovered:
                # 两层辉光晕（由亮到暗），悬停放大时一起膨胀 → 霓虹发光
                for hrad, hfill in ((br + 12, self.GLOW_FAR), (br + 5, self.GLOW_NEAR)):
                    c.create_oval(bx - hrad, by - hrad, bx + hrad, by + hrad,
                                  fill=hfill, outline="")

            c.create_oval(bx - br, by - br, bx + br, by + br,
                          fill=self.BUTTON_BG,
                          outline=self.OUTLINE_HOVER if hovered else self.OUTLINE_NORMAL,
                          width=3 if hovered else 2)
            c.create_text(bx, by, text=icon, font=self.ICON_FONT,
                          fill=self.ICON_HOVER if hovered else self.ICON_NORMAL)
            # 悬停才出字：放大过半才浮现，避免悬停瞬移闪烁
            if hovered and self._s[i] > 1.06:
                c.create_text(bx, by + br + 18, text=label,
                              font=self.LABEL_FONT, fill=self.LABEL_FILL)


class SettingsDialog:
    """Threshold + counter reset, plus idle-animation and sound-effect pickers."""

    SOUND_KEYS = ("startup", "reminder")
    SOUND_LABELS = {"startup": "启动音", "reminder": "提醒音"}

    def __init__(self, root, threshold: int, total: int, idles: list[str], current_idle: str,
                 sounds: list[str], current_sounds: dict,
                 ghost_mode: bool, pool_size: int, scale: float, on_save, on_reset, on_preview) -> None:
        # 初始化设置窗口：阈值输入、待机动画下拉、尺寸缩放、
        # 音效下拉+试听、鬼畜勾选、点击音池输入、重置/保存按钮。
        # 各下拉/输入预填当前配置值，操作都通过回调交给 app 层处理
        self.win = tk.Toplevel(root)
        self.win.title("设置")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        self._on_save = on_save
        self._on_reset = on_reset
        self._on_preview = on_preview

        frame = tk.Frame(self.win, padx=16, pady=16)
        frame.pack()

        self._total_label = tk.Label(frame, text=f"累计按键次数：{total}")
        self._total_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Label(frame, text="休息提醒阈值：").grid(row=1, column=0, sticky="w")
        self._entry = tk.Entry(frame, width=8)
        self._entry.insert(0, str(threshold))
        self._entry.grid(row=1, column=1, sticky="w")

        row = 2
        tk.Label(frame, text="待机动画：").grid(row=row, column=0, sticky="w", pady=(14, 0))
        self._idle = ttk.Combobox(frame, values=idles, state="readonly", width=16)
        self._idle.set(current_idle if current_idle in idles
                       else (idles[0] if idles else ""))
        self._idle.grid(row=row, column=1, columnspan=2, sticky="w", pady=(14, 0))

        row += 1
        tk.Label(frame, text="尺寸缩放(倍)：").grid(row=row, column=0, sticky="w", pady=(14, 0))
        self._scale_entry = tk.Entry(frame, width=8)
        self._scale_entry.insert(0, str(scale))
        self._scale_entry.grid(row=row, column=1, columnspan=2, sticky="w", pady=(14, 0))

        row += 1
        tk.Label(frame, text="音效：").grid(row=row, column=0, columnspan=3, sticky="w", pady=(14, 0))
        self._sound_cbs: dict[str, ttk.Combobox] = {}
        for key in self.SOUND_KEYS:
            row += 1
            tk.Label(frame, text=self.SOUND_LABELS[key]).grid(row=row, column=0, sticky="w")
            cb = ttk.Combobox(frame, values=sounds, state="readonly", width=14)
            current = current_sounds.get(key, "")
            cb.set(current if current in sounds else (sounds[0] if sounds else ""))
            cb.grid(row=row, column=1, sticky="w")
            tk.Button(frame, text="试听", width=4, command=lambda c=cb: self._preview(c)).grid(
                row=row, column=2, sticky="e", padx=(6, 0))
            self._sound_cbs[key] = cb

        row += 1
        self._ghost_var = tk.BooleanVar(value=bool(ghost_mode))
        tk.Checkbutton(frame, text="鬼畜模式", variable=self._ghost_var,
                       anchor="w").grid(row=row, column=0, sticky="w", pady=(14, 0))
        tk.Label(frame, text="点击音池大小（选填）：").grid(row=row, column=1, sticky="w", pady=(14, 0))
        self._pool_entry = tk.Entry(frame, width=6)
        self._pool_entry.insert(0, str(pool_size))
        self._pool_entry.grid(row=row, column=2, sticky="w", pady=(14, 0))

        row += 1
        tk.Button(frame, text="重置按键计数", command=self._reset).grid(row=row, column=0, sticky="w", pady=(14, 0))
        tk.Button(frame, text="保存", command=self._save).grid(row=row, column=1, columnspan=2, sticky="e", pady=(14, 0))

    def show(self) -> None:
        # 显示并置顶设置窗口
        self.win.deiconify()
        self.win.lift()

    def _preview(self, cb: ttk.Combobox) -> None:
        # 试听：调用 on_preview 播放所选音效文件
        name = cb.get()
        if name:
            self._on_preview(name)

    def _reset(self) -> None:
        # 重置按键计数：调用 on_reset 并把界面上的累计数字清零
        self._on_reset()
        self._total_label.config(text="累计按键次数：0")

    def _save(self) -> None:
        # 保存设置：校验阈值与池大小（必须 >0 或留空），
        # 收集所有下拉/输入的值，调用 on_save 后关闭窗口
        try:
            value = int(self._entry.get().strip())
        except ValueError:
            value = 0
        if value <= 0:
            messagebox.showwarning("设置", "阈值必须是大于 0 的整数", parent=self.win)
            return
        pool_text = self._pool_entry.get().strip()
        pool_size = None
        if pool_text:
            try:
                pool_size = int(pool_text)
            except ValueError:
                pool_size = 0
            if pool_size <= 0:
                messagebox.showwarning("设置", "池大小必须是大于 0 的整数，留空则用默认值", parent=self.win)
                return
        scale_text = self._scale_entry.get().strip()
        try:
            scale = float(scale_text)
        except ValueError:
            scale = 0.0
        if scale <= 0 or scale > 5:
            messagebox.showwarning("设置", "尺寸缩放必须是大于 0、不超过 5 的数字（如 1.0）", parent=self.win)
            return
        sounds = {key: cb.get() for key, cb in self._sound_cbs.items()}
        self._on_save(value, self._idle.get(),
                      sounds, self._ghost_var.get(), pool_size, scale)
        self.win.destroy()
