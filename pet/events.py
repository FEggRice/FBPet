"""Publish/subscribe event bus. The extension surface: any component can emit
or subscribe, so new behaviors hook in without touching the core."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable


class EventBus:
    # 发布/订阅事件总线：组件之间通过事件名解耦，互不直接引用

    def __init__(self) -> None:
        # 初始化事件名 -> 处理器列表 的映射
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> "EventBus":
        # 订阅事件：把 handler 挂到该事件名下，返回 self 支持链式调用
        self._handlers[event].append(handler)
        return self

    def emit(self, event: str, **data) -> None:
        # 广播事件：逐个调用该事件的所有订阅者，并传入 data 关键字参数
        for handler in list(self._handlers.get(event, ())):
            handler(**data)
