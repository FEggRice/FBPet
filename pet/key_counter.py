"""Per-key press counts + total. Fires reminder callbacks whenever Total
reaches a multiple of threshold (e.g. every 100 presses). Pure logic.
"""


class KeyCounter:
    # 按键计数器：按虚拟键码统计每个键的按压次数和总次数；
    # 总数每满阈值（如 100 次）就触发一次休息提醒回调

    def __init__(self, threshold: int = 100):
        # 初始化：阈值、总次数、各键计数、提醒回调列表
        self.threshold = threshold
        self.total = 0
        self._counts: dict[int, int] = {}
        self._listeners = []

    def on_reminder(self, callback) -> None:
        # 注册休息提醒回调（达到阈值时被调用，传入当前总次数）
        self._listeners.append(callback)

    def get_count(self, vk_code: int) -> int:
        # 返回某个虚拟键码的按压次数（未按过返回 0）
        return self._counts.get(vk_code, 0)

    def register(self, vk_code: int) -> None:
        # 记录一次按键：该键计数 +1、总次数 +1；
        # 总次数每满阈值就逐个调用提醒回调
        self._counts[vk_code] = self.get_count(vk_code) + 1
        self.total += 1
        if self.total % self.threshold == 0:
            for cb in self._listeners:
                cb(self.total)

    # -- persistence --------------------------------------------------------

    def to_dict(self) -> dict:
        # 导出为可序列化 dict（各键计数 + 总次数），用于写入 JSON
        return {"Counts": {str(k): v for k, v in self._counts.items()}, "Total": self.total}

    @classmethod
    def from_dict(cls, data: dict | None, threshold: int = 100) -> "KeyCounter":
        # 从 dict 恢复计数；数据缺失/损坏时容错跳过，total 非法时当 0
        c = cls(threshold)
        if not data:
            return c
        for key, value in (data.get("Counts") or {}).items():
            try:
                c._counts[int(key)] = int(value)
            except (ValueError, TypeError):
                pass
        c.total = int(data.get("Total", 0) or 0)
        return c
