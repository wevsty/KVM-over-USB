# 基于 ctypes 的全局键盘钩子
# 仅支持 Windows 平台
# 参考资料
# https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowshookexw
# https://learn.microsoft.com/windows/win32/api/winuser/ns-winuser-kbdllhookstruct
import ctypes
import ctypes.wintypes
import platform
from typing import Callable, Any, NamedTuple

from loguru import logger

if platform.system() != "Windows":
    raise ImportError("keyboard_hook only support windows")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# 键盘消息
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# 虚拟键码
# KEYEVENTF_UNICODE 注入的字符会以 vkCode = VK_PACKET 的形式出现
# 真正的 Unicode 编码由 scanCode 携带
VK_PACKET = 0xE7

# KBDLLHOOKSTRUCT.flags
LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
# 部分注入方用该位在 WM_KEYDOWN 里标记「已释放」
LLKHF_UP = 0x80

# 扫描码前缀
SCAN_PREFIX_NONE = 0x00
SCAN_PREFIX_E0 = 0xE0
# E1 仅用于 Pause/Break 的三字节序列，语义与 E0 不同层
SCAN_PREFIX_E1 = 0xE1
# Set 1 中合法前缀的白名单
KNOWN_SCAN_PREFIXES = frozenset({SCAN_PREFIX_E0, SCAN_PREFIX_E1})
# 扩展前缀集合
EXTENDED_PREFIXES = frozenset({SCAN_PREFIX_E0, SCAN_PREFIX_E1})
# Pause 的虚拟键码，用于还原丢失 E1 前缀的事件
VK_PAUSE = 0x13
# Pause 在三字节序列中的码字节
PAUSE_SCAN_CODE = 0x45

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


class ScanCodeInfo(NamedTuple):
    # 扫描码前缀：0x00 / 0xE0 / 0xE1
    prefix: int
    # 已剥掉 Break 位的码字节
    code: int
    # 是否为 Break 码(码字节带 0x80)
    is_break: bool
    # 原始 scanCode 字段值，便于排查与透传
    raw: int
    # 编码是否可信；False 时禁止用于按键身份比较
    trusted: bool
    # 是否为 VK_PACKET 携带的 UTF-16 码元
    is_unicode: bool

    @property
    def is_empty(self) -> bool:
        # 无有效扫描码(部分 Fn / ACPI 热键给 0)
        return (
            not self.is_unicode
            and self.prefix == SCAN_PREFIX_NONE
            and self.code == 0
        )

    @property
    def key_id(self) -> int | None:
        # 规范键标识(前缀 << 8 | 按码)，仅对可信且非空的结果有效
        # 按键身份请统一用该值，不要用裸 scanCode 或 vkCode
        if self.is_unicode or not self.trusted or self.is_empty:
            return None
        return (self.prefix << 8) | self.code

    @property
    def is_pause_sequence(self) -> bool:
        # E1 前缀只对应 Pause/Break 一条三字节序列
        return self.prefix == SCAN_PREFIX_E1

    # 把任意来源的 scanCode 规范化为可比对的结构
    @staticmethod
    def parse_scan_code(
        raw_scan_code: int, flags: int, vk_code: int
    ) -> ScanCodeInfo:
        # 只保留低 32 位，个别驱动会把整条序列塞进 DWORD
        raw = raw_scan_code & 0xFFFFFFFF

        # VK_PACKET 的 scanCode 是 UTF-16 码元，任何位解析都会产生假键
        # 例如 U+E0A4 的高字节恰好是 E0，会被误当成扩展前缀
        if vk_code == VK_PACKET:
            return ScanCodeInfo(
                prefix=SCAN_PREFIX_NONE,
                code=raw & 0xFFFF,
                is_break=False,
                raw=raw,
                trusted=False,
                is_unicode=True,
            )

        value = raw & 0xFFFF
        high = (value >> 8) & 0xFF
        low = value & 0xFF

        # 高字节是合法前缀：注入方已把 E0/E1 写进数值
        if high in KNOWN_SCAN_PREFIXES:
            # 前缀之后才是码字节，0x80 在此低位上仍是 Break 位
            # 前缀 + 空码(如 0xE000、HID usage 0xE0)不属于任何真实键，标记不可信
            trusted = low != 0
            return ScanCodeInfo(
                prefix=high,
                code=low & 0x7F,
                is_break=bool(low & 0x80),
                raw=raw,
                trusted=trusted,
                is_unicode=False,
            )

        # 高字节非零且不是合法前缀：脏数据或非 Set 1/HID 编码，保留但标记不可信
        if high != 0:
            return ScanCodeInfo(
                prefix=SCAN_PREFIX_NONE,
                code=low & 0x7F,
                is_break=bool(low & 0x80),
                raw=raw,
                trusted=False,
                is_unicode=False,
            )

        # Pause 的 E1 前缀在钩子里通常已丢失，仅剩 0x45
        # 用 vkCode 还原规范标识，否则会和 NumLock(0x45) 撞车
        if vk_code == VK_PAUSE and low == PAUSE_SCAN_CODE:
            return ScanCodeInfo(
                prefix=SCAN_PREFIX_E1,
                code=PAUSE_SCAN_CODE,
                is_break=False,
                raw=raw,
                trusted=True,
                is_unicode=False,
            )

        # 单字节码：扩展前缀只能来自 flags 的 EXTENDED 位
        return ScanCodeInfo(
            prefix=(
                SCAN_PREFIX_E0 if flags & LLKHF_EXTENDED else SCAN_PREFIX_NONE
            ),
            code=low & 0x7F,
            is_break=bool(low & 0x80),
            raw=raw,
            trusted=True,
            is_unicode=False,
        )


class HookKeyboardEvent:
    # 钩子键盘事件
    def __init__(
        self,
        message: int,
        vk_code: int,
        scan_code: int,
        flags: int,
        time: int,
        extra_info: int = 0,
    ):
        self.message = message
        if message in (WM_KEYDOWN, WM_SYSKEYDOWN):
            self.message_name = "key down"
        elif message in (WM_KEYUP, WM_SYSKEYUP):
            self.message_name = "key up"
        else:
            self.message_name = "unknown"
        self.flags = flags
        self.injected = bool(flags & LLKHF_INJECTED)
        # 部分注入方用 LLKHF_UP 在 WM_KEYDOWN 里标记释放
        self.up_flag = bool(flags & LLKHF_UP)
        # 虚拟键码
        self.vk_code = vk_code
        # 原始 scanCode 字段值
        self.raw_scan_code = scan_code & 0xFFFFFFFF
        # 解析一次，回调路径上不再重复计算
        self._scan_info = ScanCodeInfo.parse_scan_code(
            self.raw_scan_code, flags, vk_code
        )
        self.time = time
        # dwExtraInfo 由调用方自填，无文档保证语义
        self.extra_info = extra_info

    @property
    def scan_code_info(self) -> ScanCodeInfo:
        # 结构化的扫描码信息
        return self._scan_info

    @property
    def extended(self) -> bool:
        # 前缀可能来自 flags，也可能已被写进 scanCode 数值，统一以解析结果为准
        return self._scan_info.prefix in EXTENDED_PREFIXES

    @property
    def scan_code(self) -> int:
        # 规范扫描码：前缀 << 8 | 按码，例如 0xE036 / 0x002A / 0xE145
        # 无有效扫描码时返回 None(VK_PACKET、Fn 热键、脏数据)
        key_id = self._scan_info.key_id
        if key_id is None:
            return 0x00
        else:
            return key_id

    @property
    def is_break_code(self) -> bool:
        # 码字节带 Break 位，即硬件层的真实释放码
        return self._scan_info.is_break

    @property
    def is_packet(self) -> bool:
        # KEYEVENTF_UNICODE 注入的字符会以 vkCode = VK_PACKET 的形式出现
        return self.vk_code == VK_PACKET

    @property
    def unicode_char(self) -> str | None:
        # KEYEVENTF_UNICODE 注入时，UTF-16 码元由 scanCode 承载(对应 KEYBDINPUT.wScan)
        if not self.is_packet:
            return None
        code = self.raw_scan_code & 0xFFFF
        # 0 不是有效字符；代理对会分两次事件到达，需上层自行拼接
        # 孤立代理项(0xD800~0xDFFF)不能直接 chr，否则日志/编码处会抛 UnicodeEncodeError
        if code == 0 or 0xD800 <= code <= 0xDFFF:
            return None
        return chr(code)


# 全局键盘钩子
class KeyboardHookManager:

    def __init__(self):
        self.handler_key_down: Callable[[HookKeyboardEvent], bool] | None = None
        self.handler_key_up: Callable[[HookKeyboardEvent], bool] | None = None
        self._hook_handle = None
        # 持有回调引用防止被垃圾回收
        # noinspection bad-argument-type
        self._hook_proc_ref: Any = HOOKPROC(self._hook_proc)

    # 钩子回调（禁止在此处做耗时操作，超时会被系统静默卸载钩子）
    def _hook_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        # MSDN 规定：n_code < 0 时必须直接传递给 CallNextHookEx
        if n_code < 0:
            return user32.CallNextHookEx(None, n_code, w_param, l_param)
        if n_code != HC_ACTION:
            return user32.CallNextHookEx(None, n_code, w_param, l_param)
        if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
            handler = self.handler_key_down
        elif w_param in (WM_KEYUP, WM_SYSKEYUP):
            handler = self.handler_key_up
        else:
            handler = None
        if handler is None:
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        keyboard_struct = ctypes.cast(
            l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)
        ).contents
        event = HookKeyboardEvent(
            message=w_param,
            vk_code=keyboard_struct.vkCode,
            scan_code=keyboard_struct.scanCode,
            flags=keyboard_struct.flags,
            time=keyboard_struct.time,
            extra_info=keyboard_struct.dwExtraInfo,
        )
        # 异常绝不能穿透回调，否则事件会被吞掉且钩子可能被系统移除
        # noinspection broad-exception
        try:
            # 仅当处理函数显式返回 False 时才拦截，避免 return None 误拦截
            # noinspection calling-non-callable
            should_block = handler(event) is False
        except Exception:
            logger.exception("keyboard hook handler raised exception.")
            should_block = False
        if should_block:
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
        if not user32.UnhookWindowsHookEx(self._hook_handle):
            # 常见原因：非安装钩子的线程调用
            logger.error(
                "UnhookWindowsHookEx failed: {}",
                ctypes.WinError(ctypes.get_last_error()),
            )
        self._hook_handle = None

    # 查询键盘钩子安装状态
    def is_hooked(self) -> bool:
        return self._hook_handle is not None

    # 支持上下文管理器(进入)
    def __enter__(self) -> "KeyboardHookManager":
        return self

    # 支持上下文管理器(退出)
    def __exit__(self, exc_type, exc, tb) -> None:
        self.unhook_keyboard()

    # 确保对象析构时键盘钩子一定会被删除
    # noinspection broad-exception
    def __del__(self):
        try:
            self.unhook_keyboard()
        except Exception:
            pass


# 处理等待中的窗口消息(低级钩子回调依赖消息循环分发)
def pump_waiting_messages() -> None:
    msg = ctypes.wintypes.MSG()
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
