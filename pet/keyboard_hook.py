"""Global WH_KEYBOARD_LL hook via ctypes. Runs on its own thread with a native
message pump; raises key events (vk_code) — auto-repeat suppressed.

Callbacks run on the hook thread: hand results to the UI through a queue."""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0104, 0x0105

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class _KbdllHookStruct(ctypes.Structure):
    # 键盘钩子的消息结构体：vkCode/scanCode/flags/time/dwExtraInfo
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


_WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)

# pointer-sized return types — otherwise handles get truncated to 32-bit on x64
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _WNDPROC, ctypes.c_void_p, wintypes.DWORD]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, WPARAM, LPARAM]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


class GlobalKeyboardHook:
    # 全局键盘钩子（WH_KEYBOARD_LL，ctypes 实现）：
    # 自己跑一个线程带原生消息泵，捕获所有键盘按下，抑制按住时的自动重复

    def __init__(self) -> None:
        # 初始化：回调指针、钩子句柄、当前按住的键集合、监听器、钩子线程
        self._proc = _WNDPROC(self._callback)
        self._hook = None
        self._down: set[int] = set()
        self._listeners = []
        self._thread: threading.Thread | None = None

    def on_key(self, callback) -> None:
        # 注册按键回调（每次有效按下都会被调用，参数为虚拟键码）
        self._listeners.append(callback)

    def start(self) -> None:
        # 启动独立线程：装上 WH_KEYBOARD_LL 钩子，进入 GetMessage 消息泵循环
        def run() -> None:
            self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def _callback(self, n_code: int, w_param, l_param) -> int:
        # 钩子回调：按下时去重（忽略长按自动重复）后通知监听器；
        # 抬起时从按下集合移除；最后 CallNextHookEx 把消息放行给系统
        if n_code >= 0:
            if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                k = ctypes.cast(l_param, ctypes.POINTER(_KbdllHookStruct)).contents
                vk = int(k.vkCode)
                if vk not in self._down:  # ignore auto-repeat while key is held
                    self._down.add(vk)
                    for cb in self._listeners:
                        cb(vk)
            elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                k = ctypes.cast(l_param, ctypes.POINTER(_KbdllHookStruct)).contents
                self._down.discard(int(k.vkCode))
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    def stop(self) -> None:
        # 卸载钩子（退出程序时调用）
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
