"""Dict-backed JSON config. Kept as plain dicts so unknown/extra fields
survive a save→load round-trip — that's the extensibility surface: add a new
animation, audio key, or arbitrary setting without touching this file.
"""
from __future__ import annotations

import json
import os
from typing import Any


def default_config() -> dict:
    return {
        "window": {"width": 128, "height": 128, "transparentColor": "#ff00ff"},
        "spriteSheet": {
            "path": "pet.png",
            "cellWidth": 128,
            "cellHeight": 128,
            "cols": 8,
            "rows": 3,
        },
        "animations": {
            "idle": {"row": 0, "frames": 4, "fps": 6, "loop": True},
            "spawn": {"row": 1, "frames": 6, "fps": 10, "loop": False},
            "clicked": {"row": 2, "frames": 5, "fps": 12, "loop": False},
            "reminder": {"row": 2, "frames": 5, "fps": 8, "loop": False},
        },
        "audio": {
            "startup": "audio/startup.wav",
            "click": "audio/click.wav",
            "reminder": "audio/reminder.wav",
            "poolSize": 6,
        },
        "rest": {
            "threshold": 100,
            "messages": [
                "你已经按了 {total} 次键盘啦，起来活动一下，休息 5 分钟吧~",
                "连续敲键盘太久了，喝口水、眺望远处，眼睛也需要休息哦！",
            ],
        },
        "countFile": "key_counts.json",
    }


class PetConfig:
    """Thin typed access over the raw config dict."""

    def __init__(self, data: dict, base_dir: str):
        self.data = data
        self.base_dir = base_dir
        if "idle" not in self.animations:
            self.animations["idle"] = {"row": 0, "frames": 1, "fps": 1, "loop": True}

    # -- accessors ----------------------------------------------------------

    @property
    def animations(self) -> dict[str, dict]:
        return self.data.setdefault("animations", {})

    @property
    def rest(self) -> dict:
        return self.data.setdefault("rest", {})

    @property
    def audio(self) -> dict:
        return self.data.setdefault("audio", {})

    @property
    def sprite_sheet(self) -> dict:
        return self.data.setdefault("spriteSheet", {})

    @property
    def count_file(self) -> str:
        return self.data.get("countFile", "key_counts.json")

    def get(self, *path: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    # -- io -----------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "PetConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = default_config()
        merged.update(data)
        base = os.path.dirname(os.path.abspath(path))
        return cls(merged, base)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def resolve(self, relative: str) -> str:
        return os.path.join(self.base_dir, relative)
