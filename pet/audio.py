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
    _POOL_SIZE = 6  # 鬼畜模式：最多同时重叠的音频数

    def __init__(self) -> None:
        self._files: dict[str, str | list[str]] = {}
        self.overlap = False  # 鬼畜模式开关
        self.pool_size = self._POOL_SIZE  # 鬼畜重叠声道数，设置里可改
        self._pygame: object | None = None  # None=未初始化 / module=可用 / False=失败
        self._sounds: dict[str, object] = {}  # pygame Sound 缓存

    def set_pool_size(self, n: int) -> None:
        self.pool_size = max(1, int(n))
        if self._pygame:  # 已初始化就立刻改声道数
            try:
                self._pygame.mixer.set_num_channels(self.pool_size)
            except Exception:
                pass

    def register(self, key: str, path: str) -> None:
        if os.path.exists(path):
            self._files[key] = path

    def register_folder(self, key: str, folder: str) -> None:
        """Register a folder; play() then picks a random audio file from it."""
        if not os.path.isdir(folder):
            return
        files = sorted(os.path.join(folder, f) for f in os.listdir(folder)
                       if f.lower().endswith(_AUDIO_EXTS))
        if files:
            self._files[key] = files

    def play(self, key: str) -> None:
        entry = self._files.get(key)
        if not entry:
            return
        if isinstance(entry, list):
            entry = random.choice(entry)
        self._play_file(entry)

    def play_path(self, path: str) -> None:
        if os.path.exists(path):
            self._play_file(path)

    def _play_file(self, path: str) -> None:
        """Play a file asynchronously. Overlap (鬼畜) mode uses pygame.mixer, which
        can genuinely play many streams at once; normal mode cuts the previous
        sound via a single MCI instance (MCI mpegvideo can't overlap in audio)."""
        if self.overlap and self._ensure_pygame():
            self._play_overlap(path)
            return
        path = os.path.abspath(path).replace("\\", "/")
        dev = "mpegvideo" if path.lower().endswith(".mp3") else "waveaudio"
        _mci("close _snd", None, 0, None)  # cut the previous sound
        _mci(f'open "{path}" type {dev} alias _snd', None, 0, None)
        _mci("play _snd", None, 0, None)

    def _ensure_pygame(self):
        """Lazily init pygame.mixer (channel count = _POOL_SIZE). Returns the
        module, or False if the audio device is unavailable."""
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
        pygame = self._pygame
        snd = self._sounds.get(path)
        if snd is None:
            snd = pygame.mixer.Sound(path)
            self._sounds[path] = snd
        ch = pygame.mixer.find_channel(force=True)  # 池满就回收最老的
        if ch is not None:
            ch.play(snd)
