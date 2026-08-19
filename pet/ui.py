"""tkinter views: PetWindow (transparent topmost pet), BubbleWindow (click-through
message), SettingsDialog. Pure view layer — no business logic, all effects via callbacks."""
from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import ImageTk

from .frames import load_frames
from .radial import RadialWheel


class PetWindow:
    # 宠物主窗口：透明无边框、置顶、显示精灵帧；支持拖动、点击、右键径向轮盘

    def __init__(self, cfg, on_click, on_context) -> None:
        # 初始化：创建透明置顶无边框 tk 窗口，加载帧定尺寸，放屏幕右下角，
        # 绑定鼠标事件，建右键径向轮盘
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
        # 右键径向轮盘菜单（游戏化动效），动作仍统一走 on_context 回调
        self._radial = RadialWheel(
            self.root,
            [("chat", "对话"), ("settings", "设置"), ("hide", "隐藏到托盘"), ("quit", "退出")],
            on_select=self.on_context,
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
        self._radial.dismiss()
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
        # 右键：在鼠标位置弹出径向轮盘菜单
        self._radial.popup(e.x_root, e.y_root)


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


class SettingsDialog:
    """Threshold + counter reset, plus idle-animation and sound-effect pickers."""

    SOUND_KEYS = ("reminder",)
    SOUND_LABELS = {"reminder": "提醒音"}

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
