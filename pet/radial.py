"""Radial wheel menu geometry — pure math, no tkinter, unit-tested."""
from __future__ import annotations

import math


def button_centers(n_items: int, center: tuple[float, float], radius: float,
                   start_angle: float = 90.0) -> list[tuple[float, float]]:
    # 把 n 个按钮均匀分布在以 center 为圆心、radius 为半径的圆周上。
    # 屏幕坐标约定：0°=右，90°=上（y 向上为负），角度顺时针递增。
    # 默认 start_angle=90 让第一个按钮出现在正上方
    cx, cy = center
    step = 360.0 / n_items
    return [
        (cx + radius * math.cos(math.radians(start_angle + i * step)),
         cy - radius * math.sin(math.radians(start_angle + i * step)))
        for i in range(n_items)
    ]


def hit_test(buttons: list[tuple[float, float]], x: float, y: float,
             hit_radius: float) -> int | None:
    # 返回与 (x,y) 最近且在 hit_radius 内的按钮下标；都不在范围内返回 None
    best_i: int | None = None
    best_d = hit_radius
    for i, (bx, by) in enumerate(buttons):
        d = math.hypot(x - bx, y - by)
        if d <= best_d:
            best_i, best_d = i, d
    return best_i


def wheel_half_size(ring_radius: float, hover_radius: float, margin: float) -> float:
    # 轮盘窗口的半边长：外圈半径 + 悬停放大后按钮半径 + 边距
    return ring_radius + hover_radius + margin
