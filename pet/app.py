"""Composition root. Wires config → logic → views → OS hooks into one running pet.

Cross-thread rule: the keyboard hook and tray run on their own threads and only
push into a queue; the tkinter main thread drains it (via `_poll`). Everything
that touches tk runs on the main thread.
"""
from __future__ import annotations

import json
import os
import queue
import random
import time

from . import assets
from .animator import SpriteAnimator
from .audio import AudioPlayer
from .config import PetConfig
from .events import EventBus
from .key_counter import KeyCounter
from .keyboard_hook import GlobalKeyboardHook
from .tray import TrayIcon
from .ui import BubbleWindow, PetWindow, SettingsDialog

TICK_MS = 16      # ~60fps animation
POLL_MS = 50      # ui-queue drain
SAVE_EVERY = 60   # seconds between counter auto-saves


class PetApp:
    # 组合根：把 配置→逻辑→视图→系统钩子 全部接线成一个可运行的桌宠。
    # 跨线程约定：键盘钩子/托盘在各自线程里只往队列推事件，tk 主线程经 _poll 排空

    def __init__(self, config_path: str) -> None:
        # 初始化整只宠物：加载配置 → 生成资源 → 建音频/窗口/气泡/托盘/键盘钩子
        # → 状态机进入 spawn → 调度 _tick/_poll → 播放启动音
        self._config_path = config_path
        self.cfg = PetConfig.load(config_path)
        self.events = EventBus()

        assets.ensure_assets(self.cfg)
        self.audio = AudioPlayer()
        for key in ("startup", "reminder"):
            self.audio.register(key, self.cfg.resolve(self.cfg.audio.get(key, f"audio/{key}.wav")))
        self.audio.register_folder("click", self.cfg.resolve("audio/click"))
        self.audio.overlap = bool(self.cfg.get("audio", "overlap", default=False))
        self.audio.set_pool_size(self.cfg.get("audio", "poolSize", default=AudioPlayer._POOL_SIZE))

        self._ui_q: queue.Queue = queue.Queue()
        self._load_counter()
        self.counter.on_reminder(self._on_reminder)

        self.window = PetWindow(self.cfg, on_click=self._on_click, on_context=self._on_context)
        self.bubble = BubbleWindow(self.window.root, self.window.key)

        self.tray = TrayIcon(on_show=lambda: self._ui_q.put(("show",)),
                             on_settings=lambda: self._ui_q.put(("settings",)),
                             on_quit=lambda: self._ui_q.put(("quit",)))
        self.tray.start()

        self.hook = GlobalKeyboardHook()
        self.hook.on_key(lambda vk: self._ui_q.put(("key", vk)))
        self.hook.start()

        self._state = "idle"
        self._animator = SpriteAnimator(1, 1000, True)
        self._goto("spawn")
        self._last = time.perf_counter()
        self._last_save = time.time()
        self._settings: SettingsDialog | None = None

        self.window.root.after(TICK_MS, self._tick)
        self.window.root.after(POLL_MS, self._poll)
        self.audio.play("startup")

    # -- animation / state ---------------------------------------------------

    def _goto(self, name: str) -> None:
        # 切换动画状态：取该状态的配置和帧数重建 animator（单帧静态图强制循环），
        # 并广播 state_changed 事件
        anim = self.cfg.animations.get(name) or self.cfg.animations["idle"]
        self._state = name
        n = self.window.frame_count(name) or anim["frames"]
        # single-frame states (a static image pet) must loop, never "finish"
        self._animator = SpriteAnimator(n, 1000.0 / anim["fps"], anim.get("loop", True) or n == 1)
        self.events.emit("state_changed", state=name)

    def _tick(self) -> None:
        # 动画心跳（每 16ms）：按真实经过时间推进 animator 并显示当前帧；
        # 非 idle 状态播完后自动切回 idle，然后重调度
        now = time.perf_counter()
        self._animator.advance((now - self._last) * 1000)
        self._last = now
        self.window.show_frame(self._state, self._animator.current_frame)
        if self._animator.is_done and self._state != "idle":
            self._goto("idle")
        self.window.root.after(TICK_MS, self._tick)

    # -- cross-thread event pump ---------------------------------------------

    def _poll(self) -> None:
        # 事件泵（每 50ms）：排空跨线程队列并分发事件；每 60 秒自动保存一次计数，然后重调度
        try:
            while True:
                event = self._ui_q.get_nowait()
                self._dispatch(event)
        except queue.Empty:
            pass
        if time.time() - self._last_save > SAVE_EVERY:
            self._save_counter()
            self._last_save = time.time()
        self.window.root.after(POLL_MS, self._poll)

    def _dispatch(self, event: tuple) -> None:
        # 分发队列事件：按键（计入 counter）/ 托盘显示 / 设置 / 退出
        kind = event[0]
        if kind == "key":
            vk = event[1]
            self.counter.register(vk)
            self.events.emit("key_press", vk=vk, total=self.counter.total)
        elif kind == "show":
            self._show_from_tray()
        elif kind == "settings":
            self._open_settings()
        elif kind == "quit":
            self._quit()

    # -- behaviors -----------------------------------------------------------

    def _on_click(self) -> None:
        # 点击宠物：先播点击音（不受动画状态门控，可连点叠音）；
        # 若处于待机态则进入 clicked 动画
        self.audio.play("click")  # 音效不受动画状态门控：连点才能叠音
        if self._state == "idle":
            self._goto("clicked")

    def _on_reminder(self, total: int) -> None:
        # 休息提醒：进入 reminder 动画、播提醒音、随机选一条提示语、
        # 在宠物旁显示气泡并在 6 秒后隐藏
        self._goto("reminder")
        self.audio.play("reminder")
        msgs = self.cfg.rest.get("messages") or []
        msg = random.choice(msgs).replace("{total}", str(total)) if msgs else "休息一下吧！"
        self.bubble.show(msg, self.window.position())
        self.window.root.after(6000, self.bubble.hide)
        self.events.emit("rest_reminder", total=total)

    def _on_context(self, action: str) -> None:
        # 右键菜单动作：隐藏到托盘 / 打开设置 / 退出
        if action == "hide":
            self._hide_to_tray()
        elif action == "settings":
            self._open_settings()
        elif action == "quit":
            self._quit()

    def _hide_to_tray(self) -> None:
        # 隐藏宠物窗口、显示托盘图标
        self.window.hide()
        self.tray.show()

    def _show_from_tray(self) -> None:
        # 隐藏托盘图标、重新显示宠物窗口
        self.tray.hide()
        self.window.show()

    def _open_settings(self) -> None:
        # 打开设置窗口：已打开则置顶返回；收集候选人物/待机动画/音效与当前值，
        # 记录当前人物到 _settings_prev_character，建 SettingsDialog 并显示
        if self._settings and self._settings.win.winfo_exists():
            self._settings.win.lift()
            return
        characters = assets.discover_characters(self.cfg.base_dir)
        current_character = os.path.basename(
            self.cfg.resolve(self.cfg.sprite_sheet.get("path", "pet.png")))
        self._settings_prev_character = current_character
        idle_anim = self.cfg.animations.get("idle", {})
        current_idle = os.path.basename(self.cfg.resolve(idle_anim.get("file", "idel.gif")))
        sounds = assets.discover_sounds(self.cfg.base_dir)
        current_sounds = {key: os.path.basename(self.cfg.resolve(self.cfg.audio.get(key, f"audio/{key}.wav")))
                          for key in SettingsDialog.SOUND_KEYS}
        self._settings = SettingsDialog(
            self.window.root,
            self.cfg.rest.get("threshold", 100),
            self.counter.total,
            characters,
            current_character,
            characters,  # 待机候选 = sprites 下的 gif/png，与人物同源
            current_idle,
            sounds,
            current_sounds,
            self.cfg.get("audio", "overlap", default=False),
            self.cfg.get("audio", "poolSize", default=AudioPlayer._POOL_SIZE),
            on_save=self._on_settings_save,
            on_reset=self._on_settings_reset,
            on_preview=lambda name: self.audio.play_path(self.cfg.resolve(f"audio/{name}")),
        )
        self._settings.show()

    def _on_settings_save(self, threshold: int, character: str, idle_file: str,
                          sounds: dict, ghost_mode: bool, pool_size: int | None) -> None:
        # 保存设置：更新阈值/鬼畜/池/音效；「桌宠人物」有改动就把所有动画 file
        # 覆盖成该图（换角色）；「待机动画」只改 idle 不动 spawn；
        # 写回 config、重载帧并立即重绘窗口
        self.cfg.rest["threshold"] = threshold
        self.audio.overlap = bool(ghost_mode)
        self.cfg.audio["overlap"] = bool(ghost_mode)
        if pool_size:
            self.audio.set_pool_size(pool_size)
            self.cfg.audio["poolSize"] = pool_size
        for key, name in sounds.items():
            if name:
                self.cfg.audio[key] = f"audio/{name}"
        if character:
            self.cfg.sprite_sheet["path"] = os.path.join(assets.SPRITES_DIR, character)
            if character != getattr(self, "_settings_prev_character", ""):
                # whole-theme switch: point every state at the chosen image/gif
                for anim in self.cfg.animations.values():
                    anim["file"] = self.cfg.sprite_sheet["path"]
        if idle_file:
            # 只换待机：开场动画(spawn)保持不动
            self.cfg.animations["idle"]["file"] = os.path.join(assets.SPRITES_DIR, idle_file)
        self.cfg.save(self._config_path)
        self._replace_counter(KeyCounter.from_dict(self.counter.to_dict(), threshold))
        for key, name in sounds.items():
            if name:
                self.audio.register(key, self.cfg.resolve(self.cfg.audio.get(key)))
        sheet_path = self.cfg.sprite_sheet.get("path", "")
        if sheet_path and os.path.exists(self.cfg.resolve(sheet_path)):
            self.window.reload_frames()
            if self._state in self.cfg.animations:
                self._goto(self._state)
            # repaint immediately so the window snaps to the new size now
            self.window.show_frame(self._state, self._animator.current_frame)
            self.window.root.update_idletasks()

    def _on_settings_reset(self) -> None:
        # 重置按键计数：用当前阈值新建空 counter
        self._replace_counter(KeyCounter(self.cfg.rest.get("threshold", 100)))

    def _replace_counter(self, counter: KeyCounter) -> None:
        # 换新的计数器：重新挂提醒回调并立刻保存到文件
        self.counter = counter
        self.counter.on_reminder(self._on_reminder)
        self._save_counter()

    # -- persistence ---------------------------------------------------------

    def _load_counter(self) -> None:
        # 从 key_counts.json 加载计数（文件损坏/缺失则用空数据）
        self._count_path = self.cfg.resolve(self.cfg.count_file)
        data = None
        if os.path.exists(self._count_path):
            try:
                with open(self._count_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                data = None
        self.counter = KeyCounter.from_dict(data, self.cfg.rest.get("threshold", 100))

    def _save_counter(self) -> None:
        # 把计数写回 key_counts.json（失败静默）
        try:
            with open(self._count_path, "w", encoding="utf-8") as f:
                json.dump(self.counter.to_dict(), f)
        except OSError:
            pass

    # -- assets --------------------------------------------------------------

    # -- lifecycle -----------------------------------------------------------

    def run(self) -> None:
        # 进入 tkinter 主循环，程序在此常驻
        self.window.root.mainloop()

    def _quit(self) -> None:
        # 退出：保存计数、停键盘钩子/托盘、销毁窗口（各步容错）
        self._save_counter()
        self.hook.stop()
        self.tray.stop()
        try:
            self.window.root.quit()
            self.window.root.destroy()
        except Exception:
            pass
