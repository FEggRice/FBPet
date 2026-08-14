"""手动 GUI 冒烟：弹出轮盘 -> 跑动画循环 -> 模拟悬停/点击 -> 验证回调。
不属于 pytest 用例（文件名不以 test_ 开头），用 E:/python/python.exe 直接运行。"""
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

from pet.radial import RING_R, RadialMenu, wheel_geometry

root = tk.Tk()
root.geometry("60x60+0+0")

selected = []
dismissed = []
menu = RadialMenu(
    root,
    [("settings", "设置"), ("hide", "隐藏到托盘"), ("quit", "退出")],
    on_select=selected.append,
    on_dismiss=lambda: dismissed.append(True),
)


def pump(seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        root.update()
        time.sleep(0.01)


menu.popup(300, 300)
assert menu.is_open(), "popup 后应处于打开状态"
pump(1.2)  # 完整走完入场（0.32 + 2*0.055 ≈ 0.43s）与悬停空闲
assert len(menu._cv.find_all()) > 0, "画布上应绘制了轮盘元素"

# 悬停第 0 项（设置），再松开：两个弹簧动画都过一遍
menu._set_hover(0)
pump(0.3)
menu._set_hover(None)
pump(0.2)
menu._set_hover(1)
pump(0.3)
assert menu._cv.cget("cursor") == "hand2", "悬停时应变为手型光标"

# 点击第 0 项（设置）所在位置
tx, ty = wheel_geometry(RING_R, 3)[0]
e = types.SimpleNamespace(x_root=menu._cx + tx, y_root=menu._cy + ty)
menu._on_click(e)
assert selected == ["settings"], f"点击应选中 settings，实际 {selected}"
assert not menu.is_open(), "选中后轮盘应关闭"
assert dismissed == [True], "关闭应触发 on_dismiss"

# 贴屏幕左上角弹出：圆心应被内收，且可正常关闭
menu.popup(2, 2)
assert menu.is_open()
pump(0.1)
assert menu._cx >= menu._extent, f"圆心应内收，实际 cx={menu._cx}"
menu.dismiss()
assert not menu.is_open()

# 空白处点击仅关闭、不选中
menu.popup(300, 300)
pump(0.1)
e = types.SimpleNamespace(x_root=menu._cx, y_root=menu._cy)  # 中心枢纽
menu._on_click(e)
assert selected == ["settings"], "点空白不应追加选择"
assert not menu.is_open()

root.destroy()
print("SMOKE OK")
