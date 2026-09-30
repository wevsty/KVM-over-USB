# 基于 ctypes 的全局键盘钩子
# 仅支持 Windows 平台
# 参考资料
# https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowshookexw
# https://learn.microsoft.com/windows/win32/api/winuser/ns-winuser-kbdllhookstruct

import ctypes
import ctypes.wintypes
import platform
from typing import Callable, Any

if platform.system() != "Windows":
    raise ImportError("keyboard_hook only support windows")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# 键盘消息
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# KBDLLHOOKSTRUCT.flags
LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10

# 钩子相关常量
WH_KEYBOARD_LL = 13
HC_ACTION = 0
PM_REMOVE = 0x0001

# Windows 指针宽度类型
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
LRESULT = ctypes.c_ssize_t

# 钩子回调函数原型
HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    WPARAM,
    LPARAM,
)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


# API 参数与返回值声明
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = (
    ctypes.c_int,
    HOOKPROC,
    ctypes.c_void_p,
    ctypes.wintypes.DWORD,
)
user32.UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = (
    ctypes.c_void_p,
    ctypes.c_int,
    WPARAM,
    LPARAM,
)
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = (ctypes.wintypes.LPCWSTR,)
user32.PeekMessageW.argtypes = (
    ctypes.POINTER(ctypes.wintypes.MSG),
    ctypes.c_void_p,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
)
user32.TranslateMessage.argtypes = (ctypes.POINTER(ctypes.wintypes.MSG),)
user32.DispatchMessageW.argtypes = (ctypes.POINTER(ctypes.wintypes.MSG),)


class HookKeyboardEvent:
    # 钩子键盘事件
    def __init__(
        self,
        message: int,
        vk_code: int,
        scan_code: int,
        flags: int,
        time: int,
    ):
        self.message = message
        if message in (WM_KEYDOWN, WM_SYSKEYDOWN):
            self.message_name = "key down"
        elif message in (WM_KEYUP, WM_SYSKEYUP):
            self.message_name = "key up"
        else:
            self.message_name = "unknown"
        self.extended = bool(flags & LLKHF_EXTENDED)
        self.injected = bool(flags & LLKHF_INJECTED)
        # 虚拟键码
        self.vk_code = vk_code
        self.raw_scan_code = scan_code
        self.time = time

    @property
    def scan_code(self) -> int:
        if self.extended:
            # 扩展键(方向键/右侧修饰键等)使用 E0 前缀
            scan_code = (0xE0 << 8) | (self.raw_scan_code & 0xFF)
        else:
            scan_code = self.raw_scan_code
        return scan_code


# 全局键盘钩子
class KeyboardHookManager:

    def __init__(self):
        self.handler_key_down: Callable[[HookKeyboardEvent], bool] | None = None
        self.handler_key_up: Callable[[HookKeyboardEvent], bool] | None = None
        self._hook_handle = None
        # 持有回调引用防止被垃圾回收
        # noinspection bad-argument-type
        self._hook_proc_ref: Any = HOOKPROC(self._hook_proc)

    # 钩子回调
    def _hook_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        # MSDN 规定：若 n_code < 0，必须直接传递给 CallNextHookEx
        if n_code < 0:
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        if n_code == HC_ACTION:
            handler: Callable[[HookKeyboardEvent], bool] | None = None
            if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                handler = self.handler_key_down
            elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                handler = self.handler_key_up
            else:
                pass
            if handler:
                keyboard_struct = ctypes.cast(
                    l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)
                ).contents
                event = HookKeyboardEvent(
                    w_param,
                    keyboard_struct.vkCode,
                    keyboard_struct.scanCode,
                    keyboard_struct.flags,
                    keyboard_struct.time,
                )
                # 处理函数返回 False 时拦截按键事件
                # noinspection calling-non-callable
                result: bool = handler(event)
                if not result:
                    return 1

        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    # 安装键盘钩子
    def hook_keyboard(self) -> bool:
        if self._hook_handle is not None:
            return True
        hook_handle = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            kernel32.GetModuleHandleW(None),
            0,
        )
        if not hook_handle:
            return False
        self._hook_handle = hook_handle
        return True

    # 卸载键盘钩子
    def unhook_keyboard(self) -> None:
        if self._hook_handle is None:
            return
        user32.UnhookWindowsHookEx(self._hook_handle)
        self._hook_handle = None

    # 查询键盘钩子安装状态
    def is_hooked(self) -> bool:
        return self._hook_handle is not None

    # 确保对象析构时键盘钩子一定会被删除
    def __del__(self):
        self.unhook_keyboard()


# 处理等待中的窗口消息(低级钩子回调依赖消息循环分发)
def pump_waiting_messages() -> None:
    msg = ctypes.wintypes.MSG()
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
