"""Radial wheel menu geometry (pure math, no tk)."""
import math

from pet.radial import button_centers, hit_test, wheel_half_size


def test_button_centers_puts_first_at_top():
    centers = button_centers(3, (100, 100), 80)
    x, y = centers[0]

    assert math.isclose(x, 100, abs_tol=1e-9)  # 正上方 → 水平居中
    assert y < 100  # y 小于圆心 → 在上方


def test_button_centers_are_on_circle_and_evenly_spaced():
    centers = button_centers(3, (100, 100), 80)
    for x, y in centers:
        assert math.isclose(math.hypot(x - 100, y - 100), 80, rel_tol=1e-9)

    # 相邻按钮夹角 120° → 单位向量点积 == cos(120°) == -0.5
    vecs = [(x - 100, y - 100) for x, y in centers]
    for i in range(3):
        u = vecs[i]
        v = vecs[(i + 1) % 3]
        dot = (u[0] * v[0] + u[1] * v[1]) / (80 * 80)
        assert math.isclose(dot, -0.5, abs_tol=1e-9)


def test_hit_test_returns_nearest_index():
    centers = button_centers(3, (100, 100), 80)

    assert hit_test(centers, centers[1][0], centers[1][1], 40) == 1
    assert hit_test(centers, 100, 100, 40) is None  # 圆心处是空白


def test_hit_test_respects_radius():
    centers = button_centers(3, (100, 100), 80)
    bx, by = centers[0]

    assert hit_test(centers, bx + 39, by, 40) == 0
    assert hit_test(centers, bx + 41, by, 40) is None


def test_wheel_half_size():
    assert wheel_half_size(88, 46, 6) == 140
