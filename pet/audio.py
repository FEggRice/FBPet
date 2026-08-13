"""Sound effects via Windows MCI (ctypes → winmm.dll). Plays WAV *and* MP3
without extra deps. Fire-and-forget: each new sound cuts the previous one."""
from __future__ import annotations

import ctypes
import os
import random

_mci = ctypes.windll.winmm.mciSendStringW
_mci.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]

_AUDIO_EXTS = (".mp3", ".wav")


class AudioPlayer:
    # 音效播放器：普通模式用 Windows MCI（新音效切掉上一个）；
    # 鬼畜模式开启后用 pygame.mixer 真多声道重叠播放

    _POOL_SIZE = 6  # 鬼畜模式：最多同时重叠的音频数

    def __init__(self) -> None:
        # 初始化：空注册表、鬼畜开关、声道池大小、pygame 懒加载状态与 Sound 缓存
        self._files: dict[str, str | list[str]] = {}
        self.overlap = False  # 鬼畜模式开关
        self.pool_size = self._POOL_SIZE  # 鬼畜重叠声道数，设置里可改
        self._pygame: object | None = None  # None=未初始化 / module=可用 / False=失败
        self._sounds: dict[str, object] = {}  # pygame Sound 缓存

    def set_pool_size(self, n: int) -> None:
        # 设置鬼畜声道池大小（最小 1）；pygame 已初始化就同步修改声道数
        self.pool_size = max(1, int(n))
        if self._pygame:  # 已初始化就立刻改声道数
            try:
                self._pygame.mixer.set_num_channels(self.pool_size)
            except Exception:
                pass

    def register(self, key: str, path: str) -> None:
        # 把单个音频文件注册到某个键名下（文件不存在则忽略）
        if os.path.exists(path):
            self._files[key] = path

    def register_folder(self, key: str, folder: str) -> None:
        # 把整个文件夹注册到键名下，play() 时从其中随机选一个播放
        if not os.path.isdir(folder):
            return
        files = sorted(os.path.join(folder, f) for f in os.listdir(folder)
                       if f.lower().endswith(_AUDIO_EXTS))
        if files:
            self._files[key] = files

    def play(self, key: str) -> None:
        # 按键名播放音频；若该键对应一个文件夹列表则随机挑一个
        entry = self._files.get(key)
        if not entry:
            return
        if isinstance(entry, list):
            entry = random.choice(entry)
        self._play_file(entry)

    def play_path(self, path: str) -> None:
        # 直接播放指定路径的文件（如设置里的"试听"）
        if os.path.exists(path):
            self._play_file(path)

    def _play_file(self, path: str) -> None:
        # 播放单个文件：鬼畜模式走 pygame 多声道；否则 MCI 先 close 旧音再播新的
        # （普通模式单声道，新音效会切掉上一个）
        if self.overlap and self._ensure_pygame():
            self._play_overlap(path)
            return
        path = os.path.abspath(path).replace("\\", "/")
        dev = "mpegvideo" if path.lower().endswith(".mp3") else "waveaudio"
        _mci("close _snd", None, 0, None)  # cut the previous sound
        _mci(f'open "{path}" type {dev} alias _snd', None, 0, None)
        _mci("play _snd", None, 0, None)

    def _ensure_pygame(self):
        # 懒初始化 pygame.mixer（声道数 = 池大小）；音频设备不可用时返回 False
        if self._pygame is None:
            try:
                os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
                import pygame
                pygame.mixer.init()
                pygame.mixer.set_num_channels(self.pool_size)
                self._pygame = pygame
            except Exception:
                self._pygame = False
        return self._pygame

    def _play_overlap(self, path: str) -> None:
        # pygame 重叠播放：缓存 Sound 对象；find_channel(force=True) 池满时回收最老的声道
        pygame = self._pygame
        snd = self._sounds.get(path)
        if snd is None:
            snd = pygame.mixer.Sound(path)
            self._sounds[path] = snd
        ch = pygame.mixer.find_channel(force=True)  # 池满就回收最老的
        if ch is not None:
            ch.play(snd)
