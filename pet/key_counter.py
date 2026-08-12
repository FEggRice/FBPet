"""Per-key press counts + total. Fires reminder callbacks whenever Total
reaches a multiple of threshold (e.g. every 100 presses). Pure logic.
"""


class KeyCounter:
    def __init__(self, threshold: int = 100):
        self.threshold = threshold
        self.total = 0
        self._counts: dict[int, int] = {}
        self._listeners = []

    def on_reminder(self, callback) -> None:
        self._listeners.append(callback)

    def get_count(self, vk_code: int) -> int:
        return self._counts.get(vk_code, 0)

    def register(self, vk_code: int) -> None:
        self._counts[vk_code] = self.get_count(vk_code) + 1
        self.total += 1
        if self.total % self.threshold == 0:
            for cb in self._listeners:
                cb(self.total)

    # -- persistence --------------------------------------------------------

    def to_dict(self) -> dict:
        return {"Counts": {str(k): v for k, v in self._counts.items()}, "Total": self.total}

    @classmethod
    def from_dict(cls, data: dict | None, threshold: int = 100) -> "KeyCounter":
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
