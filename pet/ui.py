"""tkinter views: PetWindow (transparent topmost pet), BubbleWindow (click-through
message), SettingsDialog. Pure view layer — no business logic, all effects via callbacks."""
from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import messagebox

from PIL import ImageTk

from .frames import load_frames


class PetWindow:
    def __init__(self, cfg, on_click, on_context) -> None:
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
        self._context = tk.Menu(self.root, tearoff=0)
        self._context.add_command(label="隐藏到托盘", command=lambda: self.on_context("hide"))
        self._context.add_command(label="设置", command=lambda: self.on_context("settings"))
        self._context.add_separator()
        self._context.add_command(label="退出", command=lambda: self.on_context("quit"))

    # -- view ----------------------------------------------------------------

    def show_frame(self, state: str, index: int) -> None:
        imgs = self.frames.get(state)
        if imgs and index < len(imgs):
            self._label.config(image=imgs[index])

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()

    def position(self) -> tuple[int, int, int, int]:
        return (self.root.winfo_x(), self.root.winfo_y(),
                self.root.winfo_width(), self.root.winfo_height())

    def frame_count(self, state: str) -> int:
        return len(self.frames.get(state) or [])

    def _load_frames(self) -> tuple[dict[str, list], tuple[int, int]]:
        sheet = self.cfg.sprite_sheet
        path = self.cfg.resolve(sheet.get("path", "pet.png"))
        box = (
            self.cfg.get("window", "width", default=128),
            self.cfg.get("window", "height", default=128),
        )
        frames, size = load_frames(path, sheet, self.cfg.animations, box)
        return {name: [ImageTk.PhotoImage(im, master=self.root) for im in imgs] for name, imgs in frames.items()}, size

    # -- input ---------------------------------------------------------------

    def _on_down(self, e) -> None:
        self._drag_start = (e.x_root, e.y_root)
        self._moved = False

    def _on_move(self, e) -> None:
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
        if self._drag_start and not self._moved:
            self.on_click()
        self._drag_start = None

    def _on_right(self, e) -> None:
        try:
            self._context.tk_popup(e.x_root, e.y_root)
        finally:
            self._context.grab_release()


class BubbleWindow:
    """Click-through topmost bubble shown next to the pet. Uses FindWindow by a
    unique title to grab its HWND and set WS_EX_TRANSPARENT so clicks pass through."""

    _TITLE = "_fb_pet_bubble_"

    def __init__(self, root, key: str) -> None:
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
        self._win.withdraw()

    def _make_click_through(self) -> None:
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
    def __init__(self, root, threshold: int, total: int, on_save, on_reset) -> None:
        self.win = tk.Toplevel(root)
        self.win.title("设置")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        frame = tk.Frame(self.win, padx=16, pady=16)
        frame.pack()
        self._total_label = tk.Label(frame, text=f"累计按键次数：{total}")
        self._total_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        tk.Label(frame, text="休息提醒阈值：").grid(row=1, column=0, sticky="w")
        self._entry = tk.Entry(frame, width=8)
        self._entry.insert(0, str(threshold))
        self._entry.grid(row=1, column=1, sticky="w")
        tk.Button(frame, text="重置按键计数", command=self._reset).grid(row=2, column=0, sticky="w", pady=(12, 0))
        tk.Button(frame, text="保存", command=self._save).grid(row=2, column=1, sticky="e", pady=(12, 0))

        self._on_save = on_save
        self._on_reset = on_reset

    def show(self) -> None:
        self.win.deiconify()
        self.win.lift()

    def _reset(self) -> None:
        self._on_reset()
        self._total_label.config(text="累计按键次数：0")

    def _save(self) -> None:
        try:
            value = int(self._entry.get().strip())
        except ValueError:
            value = 0
        if value <= 0:
            messagebox.showwarning("设置", "阈值必须是大于 0 的整数", parent=self.win)
            return
        self._on_save(value)
        self.win.destroy()
