"""Publish/subscribe event bus. The extension surface: any component can emit
or subscribe, so new behaviors hook in without touching the core."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> "EventBus":
        self._handlers[event].append(handler)
        return self

    def emit(self, event: str, **data) -> None:
        for handler in list(self._handlers.get(event, ())):
            handler(**data)
