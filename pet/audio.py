"""Sound effects via winsound (stdlib). Play is fire-and-forget."""
from __future__ import annotations

import os
import winsound


class AudioPlayer:
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def register(self, key: str, path: str) -> None:
        if os.path.exists(path):
            self._files[key] = path

    def play(self, key: str) -> None:
        path = self._files.get(key)
        if path:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
