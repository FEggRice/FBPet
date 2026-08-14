import math

import pytest

from pet.radial import (
    OVERSHOOT,
    clamp,
    clamp_center,
    ease_out_back,
    ease_out_cubic,
    mix_color,
    pick_item,
    wheel_geometry,
)


def test_overshoot_constant_is_spec_value():
    # 弹簧过冲系数按需求固定为 1.438
    assert OVERSHOOT == 1.438


def test_ease_out_back_endpoints_and_overshoot():
    assert ease_out_back(0.0) == pytest.approx(0.0)
    assert ease_out_back(1.0) == pytest.approx(1.0)
    # 中间段应出现过冲（峰值 > 1），随后回落收在 1.0
    peak = max(ease_out_back(t / 200) for t in range(201))
    assert peak > 1.0
    assert all(ease_out_back(t / 200) >= 0.0 for t in range(201))


def test_ease_out_back_is_monotonic_up_to_peak():
    # 峰值前单调上升（峰值在 t≈0.607，之后过冲回落，不能要求全程单调）
    samples = [ease_out_back(t / 100) for t in range(61)]
    assert all(a <= b + 1e-9 for a, b in zip(samples, samples[1:]))


def test_ease_out_cubic_endpoints_and_midpoint():
    assert ease_out_cubic(0.0) == 0.0
    assert ease_out_cubic(1.0) == 1.0
    assert ease_out_cubic(0.5) == 0.875


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_wheel_geometry_three_items_start_at_top_clockwise():
    pts = wheel_geometry(ring_r=92, count=3)
    assert len(pts) == 3
    x0, y0 = pts[0]
    assert x0 == pytest.approx(0) and y0 == pytest.approx(-92)  # 第 0 项朝正上方
    for i, (x, y) in enumerate(pts):
        assert math.hypot(x, y) == pytest.approx(92)
        ang = math.degrees(math.atan2(y, x))
        assert round(ang - (-90 + i * 120)) % 360 == 0


def test_clamp_center_keeps_wheel_on_screen():
    # 屏幕 1920x1080，轮盘半径 190：贴右下角时圆心内收
    assert clamp_center(960, 540, 190, 1920, 1080) == (960, 540)
    assert clamp_center(1900, 1050, 190, 1920, 1080) == (1730, 890)
    assert clamp_center(5, 5, 190, 1920, 1080) == (190, 190)


def test_pick_item_hits_each_button():
    # 圆心在原点：上方 → 设置(0)，右下 → 隐藏(1)，左下 → 退出(2)
    assert pick_item(0, -92, 92, 40, 3) == 0
    assert pick_item(92 * math.cos(math.radians(30)), 92 * math.sin(math.radians(30)), 92, 40, 3) == 1
    assert pick_item(92 * math.cos(math.radians(150)), 92 * math.sin(math.radians(150)), 92, 40, 3) == 2


def test_pick_item_misses_center_and_far_outside():
    assert pick_item(0, 0, 92, 40, 3) is None        # 中心枢纽不命中
    assert pick_item(300, 0, 92, 40, 3) is None      # 环带之外
    assert pick_item(10, -10, 92, 40, 3) is None     # 环带之内侧


def test_pick_item_respects_band():
    # 刚好在环带外沿内侧命中，超出一像素不命中
    assert pick_item(0, -(92 + 39), 92, 40, 3) == 0
    assert pick_item(0, -(92 + 41), 92, 40, 3) is None


def test_mix_color_endpoints_and_midpoint():
    assert mix_color("#000000", "#ffffff", 0.0) == "#000000"
    assert mix_color("#000000", "#ffffff", 1.0) == "#ffffff"
    assert mix_color("#000000", "#ffffff", 0.5) == "#808080"
    assert mix_color("#22d3ee", "#ffffff", 1.5) == "#ffffff"
