"""Dict-backed JSON config. Kept as plain dicts so unknown/extra fields
survive a save→load round-trip — that's the extensibility surface: add a new
animation, audio key, or arbitrary setting without touching this file.
"""
from __future__ import annotations

import json
import os
from typing import Any


def default_config() -> dict:
    # 生成默认配置字典：窗口尺寸/透明色、精灵表规格、四组动画参数、
    # 音效、休息阈值与提示语、计数文件名
    return {
        "window": {"width": 128, "height": 128, "transparentColor": "#ff00ff", "scale": 1.0},
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
        "agent": {
            "host": "127.0.0.1",
            "port": 8000,
            "python": "E:\\CountBot\\venv\\Scripts\\python.exe",
            "dir": "FBeePet",
        },
        "countFile": "key_counts.json",
    }


class PetConfig:
    """Thin typed access over the raw config dict."""

    def __init__(self, data: dict, base_dir: str):
        # 初始化：保存原始配置字典和基目录，并确保动画里必有 idle
        self.data = data
        self.base_dir = base_dir
        if "idle" not in self.animations:
            self.animations["idle"] = {"row": 0, "frames": 1, "fps": 1, "loop": True}

    # -- accessors ----------------------------------------------------------

    @property
    def animations(self) -> dict[str, dict]:
        # 取"动画"子字典（不存在则创建一个空字典）
        return self.data.setdefault("animations", {})

    @property
    def rest(self) -> dict:
        # 取"休息提醒"子字典
        return self.data.setdefault("rest", {})

    @property
    def audio(self) -> dict:
        # 取"音效"子字典
        return self.data.setdefault("audio", {})

    @property
    def sprite_sheet(self) -> dict:
        # 取"精灵表"子字典
        return self.data.setdefault("spriteSheet", {})

    @property
    def count_file(self) -> str:
        # 返回计数文件名（默认 key_counts.json）
        return self.data.get("countFile", "key_counts.json")

    def get(self, *path: str, default: Any = None) -> Any:
        # 按点分路径逐层取值，如 get("window","width")；某层缺失就返回默认值
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    # -- io -----------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "PetConfig":
        # 从 JSON 文件读配置，与默认配置合并补齐缺失字段；基目录取配置所在目录
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = default_config()
        merged.update(data)
        base = os.path.dirname(os.path.abspath(path))
        return cls(merged, base)

    def save(self, path: str) -> None:
        # 把当前配置写回 JSON 文件（保留中文，带缩进）
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def resolve(self, relative: str) -> str:
        # 相对路径拼成绝对路径：基目录 + 相对路径
        return os.path.join(self.base_dir, relative)
