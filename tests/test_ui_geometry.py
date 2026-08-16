"""Radial wheel menu geometry (pure math, no tk)."""
import math

from pet.radial import clamp_center, pick_item, wheel_geometry


def test_wheel_geometry_puts_first_at_top():
    centers = wheel_geometry(80, 3)
    x, y = centers[0]

    assert math.isclose(x, 0.0, abs_tol=1e-9)  # 正上方 → 水平居中
    assert y < 0  # y 为负 → 在圆心上方


def test_wheel_geometry_on_circle_and_evenly_spaced():
    centers = wheel_geometry(80, 3)
    for x, y in centers:
        assert math.isclose(math.hypot(x, y), 80, rel_tol=1e-9)

    # 相邻按钮夹角 120° → 单位向量点积 == cos(120°) == -0.5
    for i in range(3):
        u = centers[i]
        v = centers[(i + 1) % 3]
        dot = (u[0] * v[0] + u[1] * v[1]) / (80 * 80)
        assert math.isclose(dot, -0.5, abs_tol=1e-9)


def test_pick_item_returns_sector_index():
    # 扇区从正上方(-90°)起顺时针排布，命中检测用 ring_r ± band 的圆环带
    x0, y0 = wheel_geometry(80, 3)[0]
    x1, y1 = wheel_geometry(80, 3)[1]
    x2, y2 = wheel_geometry(80, 3)[2]
    assert pick_item(x0, y0, 80, 10, 3) == 0  # 正上方按钮
    assert pick_item(x1, y1, 80, 10, 3) == 1  # 右下方按钮
    assert pick_item(x2, y2, 80, 10, 3) == 2  # 左下方按钮


def test_pick_item_none_outside_band():
    assert pick_item(0, 0, 80, 10, 3) is None     # 圆心处是空白
    assert pick_item(0, -40, 80, 10, 3) is None   # 半径太小
    assert pick_item(0, -120, 80, 10, 3) is None  # 半径太大


def test_clamp_center_keeps_wheel_on_screen():
    assert clamp_center(-100, 0, 140, 1024, 768) == (140, 140)
    assert clamp_center(2000, 900, 140, 1024, 768) == (1024 - 140, 768 - 140)
