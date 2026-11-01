#!/usr/bin/env python3
"""KVM 控制器上位机联调客户端（协议依据：docs/PROTOCOL.md v1.4）

链路：CH343 UART（默认 COM5，115200 8N1）
    上位机 --协议帧--> 控制器 --HID/CDC--> 目标机

用法示例：
    python tools/kvm_client.py selfcheck            纯逻辑自检（不打开串口）
    python tools/kvm_client.py monitor -n 10        只接收并解码 10 秒
    python tools/kvm_client.py status               同步到 CONTROL 并查键盘状态
    python tools/kvm_client.py enter                同步到 CONTROL
    python tools/kvm_client.py exit                 安全退出到 PASSTHROUGH
    python tools/kvm_client.py reset                重启控制器（USB 会重新枚举）
    python tools/kvm_client.py ping --tag 0x11
    python tools/kvm_client.py query
    python tools/kvm_client.py key --modifier 0x02 --key 0x04
    python tools/kvm_client.py text "hello"
    python tools/kvm_client.py mrel --dx 10 --dy 10
    python tools/kvm_client.py mabs --x 0 --y 0
    python tools/kvm_client.py demo                 正向用例（需人工观察）
    python tools/kvm_client.py test                 异常用例

要点：
  * 打开串口时 DTR/RTS 都不拉高，避免 CH343 自动下载电路把芯片复位（AGENTS.md 第 14 条）。
  * 固件日志与协议帧在 COM5 混流属预期现象，解析器按 MAGIC + FNV 过滤（§16.1）。
  * 控制器复位后模式回到 PASSTHROUGH，必须重新 enter（§14.5）。
  * reset 会让目标机的 USB 设备消失再出现（§4.5），目标机侧 CDC 句柄必然失效。
  * 本工具只做"请求-响应"，不会主动发协议帧给控制器（除命令要求的帧）。
"""

from __future__ import annotations

import argparse
import ast
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

try:
    import serial
except ImportError:  # pragma: no cover
    print("缺少 pyserial：pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

# ============================================================================
# 协议常量（docs/PROTOCOL.md v1.4；冻结协议，实现不得擅自改动）
# ============================================================================

MAGIC = b"\x4B\x56\x4D\x00\xA5\x5A\xC3\x3C"
PROTO_VERSION = 0x01
MAX_PAYLOAD = 1024
HEADER_LEN = 12          # MAGIC(8) + VERSION(1) + TYPE(1) + LENGTH(2)
CHECK_LEN = 4            # FNV1A32 小端

T_ENTER = 0x01
T_EXIT = 0x02
T_RESET = 0x03
T_KEYBOARD = 0x10
T_MOUSE_REL = 0x11
T_MOUSE_ABS = 0x12
T_KBD_STATE = 0x13
T_QUERY = 0x14
T_PING = 0x20
T_PONG = 0x21

TYPE_NAMES = {
    T_ENTER: "ENTER_CONTROL",
    T_EXIT: "EXIT_CONTROL",
    T_RESET: "RESET",
    T_KEYBOARD: "KEYBOARD",
    T_MOUSE_REL: "MOUSE_REL",
    T_MOUSE_ABS: "MOUSE_ABS",
    T_KBD_STATE: "REPORT_KEYBOARD_STATE",
    T_QUERY: "QUERY_KEYBOARD_STATE",
    T_PING: "PING",
    T_PONG: "PONG",
}

# 协议 §6 规定的 PAYLOAD 长度（未知 TYPE 不在表中）
PAYLOAD_LEN = {
    T_ENTER: 0,
    T_EXIT: 0,
    T_RESET: 0,
    T_KEYBOARD: 8,
    T_MOUSE_REL: 4,
    T_MOUSE_ABS: 6,
    T_KBD_STATE: 1,
    T_QUERY: 0,
    T_PING: 1,
    T_PONG: 4,
}

TYPE_BY_NAME = {name: t for t, name in TYPE_NAMES.items()}

# 超时与重试（§12.4 / §14.1 / §14.4 / §14.5）
PING_TIMEOUT = 0.100
QUERY_TIMEOUT = 0.100
SYNC_RETRIES = 3
SYNC_SETTLE = 0.020
EXIT_DRAIN = 0.100
QUERY_INTERVAL = 0.200      # §11.6：轮询间隔 >= 200 ms
# RESET（§14.6）：等待芯片重启 + USB 重新枚举，再判定成败并重新同步
RESET_SETTLE = 1.0
RESET_SYNC_RETRIES = 3
RESET_SYNC_DELAY = 0.5

# 人工观察停留（AGENTS.md：需要人眼确认的一律 2000 ms）
HUMAN_OBSERVE = 2.0


# ============================================================================
# 输出与格式
# ============================================================================

def hexs(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def type_name(t: int) -> str:
    return TYPE_NAMES.get(t, f"UNKNOWN(0x{t:02X})")


def payload_len(t: int) -> int:
    """§6 规定的 PAYLOAD 长度；未定义返回 -1"""
    return PAYLOAD_LEN.get(t, -1)


class Checker:
    """统一 PASS/FAIL 计数与输出（selfcheck / test 共用）"""

    def __init__(self, title: str) -> None:
        self.passed = 0
        self.failed = 0
        print(f"\n=== {title} ===")

    def check(self, ok: bool, what: str, detail: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  [PASS] {what}")
        else:
            self.failed += 1
            extra = f" -> {detail}" if detail else ""
            print(f"  [FAIL] {what}{extra}")
        return ok

    def summary(self) -> bool:
        total = self.passed + self.failed
        print()
        if self.failed == 0:
            print(f"全部通过：{total}/{total}")
            return True
        print(f"失败 {self.failed} 项，通过 {self.passed} 项，共 {total} 项")
        return False


def info(msg: str) -> None:
    print(f"  {msg}")


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


# ============================================================================
# 编解码：FNV-1a-32 / 帧构造（§5 / §7）
# ============================================================================

FNV_OFFSET = 0x811C9DC5
FNV_PRIME = 0x01000193
MASK32 = 0xFFFFFFFF


def fnv1a32(data: bytes) -> int:
    """FNV-1a-32（§7.1）：32 位自然回绕，计算范围 VERSION..PAYLOAD（§7.2）"""
    h = FNV_OFFSET
    for b in data:
        h = ((h ^ b) * FNV_PRIME) & MASK32
    return h


def build_frame(type_: int, payload: bytes = b"") -> bytes:
    """构造完整帧：MAGIC + VERSION + TYPE + LENGTH(LE) + PAYLOAD + FNV(LE)"""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"PAYLOAD 超长：{len(payload)} > {MAX_PAYLOAD}（§5.3）")
    expected = payload_len(type_)
    if expected >= 0 and expected != len(payload):
        warn(f"TYPE={type_name(type_)} 的 PAYLOAD 应为 {expected} 字节，实际 {len(payload)}"
             f"（固件会按 B 类整帧丢弃，§15.2）")
    header = bytes([PROTO_VERSION, type_]) + len(payload).to_bytes(2, "little")
    signed = header + payload
    return MAGIC + signed + fnv1a32(signed).to_bytes(4, "little")


@dataclass
class Frame:
    type: int
    payload: bytes
    raw: bytes = field(repr=False, default=b"")
    fnv: int = 0

    @property
    def name(self) -> str:
        return type_name(self.type)

    def __str__(self) -> str:
        return f"{self.name} len={len(self.payload)} payload=[{hexs(self.payload)}]"


class Parser:
    """流式解析器（§13.3 上位机侧等价实现）

    与固件同构：MAGIC 前缀匹配 -> 头部校验 -> 收满 -> FNV 校验。
    差异：§15.1 的"回退转发"在上位机没有意义，非帧字节直接丢弃并计数。
    """

    def __init__(self) -> None:
        self.buf = bytearray()
        self.skipped = 0
        self.bad_fnv = 0
        self.stray: list[Frame] = []

    def feed(self, data: bytes) -> None:
        self.buf.extend(data)

    def pop_frames(self) -> list[Frame]:
        frames: list[Frame] = []
        buf = self.buf
        while True:
            n = len(buf)
            if n == 0:
                break

            # 1) MAGIC 前缀匹配
            k = 0
            while k < n and k < len(MAGIC) and buf[k] == MAGIC[k]:
                k += 1
            if k < len(MAGIC):
                if k == n:            # 全是前缀，等更多字节
                    break
                drop = k if k > 0 else 1
                del buf[:drop]
                self.skipped += drop
                continue

            # 2) 头部
            if n < HEADER_LEN:
                break
            if buf[8] != PROTO_VERSION:
                del buf[:1]           # A 类（§15.1）
                self.skipped += 1
                continue
            length = buf[10] | (buf[11] << 8)
            if length > MAX_PAYLOAD:
                del buf[:1]           # A 类（§15.1）
                self.skipped += 1
                continue

            # 3) 收满
            total = HEADER_LEN + length + CHECK_LEN
            if n < total:
                break

            # 4) FNV 校验
            calc = fnv1a32(bytes(buf[8:HEADER_LEN + length]))
            recv = int.from_bytes(buf[HEADER_LEN + length:total], "little")
            if calc != recv:
                del buf[:1]           # A 类：前移 1 字节重扫（§13.2 第 2 条）
                self.bad_fnv += 1
                continue

            # 5) 帧成立
            frames.append(Frame(
                type=buf[9],
                payload=bytes(buf[HEADER_LEN:HEADER_LEN + length]),
                raw=bytes(buf[:total]),
                fnv=recv,
            ))
            del buf[:total]
        return frames


# ============================================================================
# 串口封装（COM5 = CH343；DTR/RTS 都不拉高，见 AGENTS.md 第 14 条）
# ============================================================================

def to_byte(value: int, name: str) -> int:
    """-128~255 -> 0~255（负数按二补码），用于 int8 字段（§9 / §10）"""
    if not -128 <= value <= 255:
        raise ValueError(f"{name} 超出范围：{value}（允许 -128~255）")
    return value & 0xFF


def to_abs16(value: int, name: str) -> bytes:
    """绝对坐标 0~32767 -> 2 字节小端（§10.1）"""
    if not 0 <= value <= 32767:
        raise ValueError(f"{name} 超出范围：{value}（协议 §10.1 允许 0~32767）")
    return value.to_bytes(2, "little")


class KvmPort:
    def __init__(self, name: str, baud: int = 115200) -> None:
        self.name = name
        self.parser = Parser()
        self.ser = serial.Serial()
        self.ser.port = name
        self.ser.baudrate = baud
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.timeout = 0
        self.ser.write_timeout = 1.0
        # 打开前先置低，避免 CH343 的 DTR/RTS 自动下载电路把芯片拉进下载/复位
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.open()
        time.sleep(0.1)
        self.ser.reset_input_buffer()

    # --- 生命周期 ---
    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass

    def __enter__(self) -> "KvmPort":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # --- 原始收发 ---
    def write(self, data: bytes, label: Optional[str] = None, show: bool = True) -> None:
        if show:
            prefix = f"{label}: " if label else ""
            info(f"TX  {prefix}{hexs(data)}")
        self.ser.write(data)
        self.ser.flush()

    def pump(self, duration: float) -> list[Frame]:
        """读取 duration 秒内到达的字节并解帧（日志噪声自动丢弃并计数）"""
        frames: list[Frame] = []
        deadline = time.monotonic() + duration
        while True:
            pending = self.ser.in_waiting
            if pending:
                self.parser.feed(self.ser.read(pending))
                frames.extend(self.parser.pop_frames())
            if time.monotonic() >= deadline:
                break
            if not pending:
                time.sleep(0.002)
        return frames

    def wait_frame(self, expect_type: Optional[int] = None,
                   expect_tag: Optional[int] = None,
                   timeout: float = PING_TIMEOUT) -> Optional[Frame]:
        """等待第一个符合条件（TYPE / PAYLOAD[0] tag）的帧；不匹配的进 stray"""
        deadline = time.monotonic() + timeout
        found: Optional[Frame] = None
        while time.monotonic() < deadline and found is None:
            for f in self.pump(0.005):
                matched = expect_type is None or f.type == expect_type
                if matched and expect_tag is not None:
                    matched = len(f.payload) >= 1 and f.payload[0] == expect_tag
                if matched and found is None:
                    found = f
                else:
                    self.parser.stray.append(f)
        return found

    # --- 上行帧 ---
    def send_type(self, type_: int, payload: bytes = b"", show: bool = True) -> None:
        self.write(build_frame(type_, payload), show=show)

    def ping(self, tag: int, timeout: float = PING_TIMEOUT, show: bool = True) -> Optional[Frame]:
        t = tag & 0xFF
        self.send_type(T_PING, bytes([t]), show=show)
        return self.wait_frame(T_PONG, t, timeout)

    def query(self, show: bool = True) -> Optional[Frame]:
        self.send_type(T_QUERY, show=show)
        return self.wait_frame(T_KBD_STATE, None, QUERY_TIMEOUT)

    def keyboard(self, modifier: int = 0, keys: Iterable[int] = (), show: bool = True) -> None:
        """KEYBOARD：8 字节 Boot 报告，6KRO（§8）；不足 6 键补 0x00"""
        kc = [k & 0xFF for k in keys]
        if len(kc) > 6:
            raise ValueError(f"6KRO：最多 6 个键，实际 {len(kc)}（§8.3）")
        payload = bytes([modifier & 0xFF, 0x00] + kc + [0] * (6 - len(kc)))
        self.send_type(T_KEYBOARD, payload, show=show)

    def mouse_rel(self, buttons: int = 0, dx: int = 0, dy: int = 0,
                  wheel: int = 0, show: bool = True) -> None:
        payload = bytes([to_byte(buttons, "Buttons"), to_byte(dx, "Dx"),
                         to_byte(dy, "Dy"), to_byte(wheel, "Wheel")])
        self.send_type(T_MOUSE_REL, payload, show=show)

    def mouse_abs(self, buttons: int = 0, x: int = 0, y: int = 0,
                  wheel: int = 0, show: bool = True) -> None:
        payload = (bytes([to_byte(buttons, "Buttons")]) + to_abs16(x, "X")
                   + to_abs16(y, "Y") + bytes([to_byte(wheel, "Wheel")]))
        self.send_type(T_MOUSE_ABS, payload, show=show)

    def sync_control(self, tag_base: int = 0x11) -> bool:
        """§14.1：ENTER_CONTROL -> 20 ms -> PING；连续 3 次失败即放弃（§14.5）

        ENTER_CONTROL 是幂等的（§4.3），控制器复位后会回到 PASSTHROUGH（§14.5），
        所以每次重试都重发 ENTER 再 PING，用 PONG 的 mode 位确认真的进了 CONTROL。
        """
        for i in range(SYNC_RETRIES):
            tag = (tag_base + i) & 0xFF
            info(f"同步尝试 {i + 1}/{SYNC_RETRIES}：ENTER_CONTROL + PING(tag=0x{tag:02X})")
            self.send_type(T_ENTER)
            time.sleep(SYNC_SETTLE)
            pong = self.ping(tag)
            if pong is None:
                warn(f"PING 超时（{int(PING_TIMEOUT * 1000)} ms，§14.5）")
                continue
            print_pong(pong)
            if len(pong.payload) >= 2 and pong.payload[1] == 1:
                return True
            warn("PONG 的 mode 仍是 PASSTHROUGH，继续重试")
        return False

    def exit_control(self) -> list[Frame]:
        """§14.4：全释放键盘 -> 鼠标按键清零 -> EXIT_CONTROL -> 排空 100 ms"""
        self.keyboard(0, (), show=False)
        time.sleep(SYNC_SETTLE)
        self.mouse_rel(0, 0, 0, 0, show=False)
        time.sleep(SYNC_SETTLE)
        info("TX  全释放键盘报告 + 鼠标按键清零（§14.4 第 1~2 步）")
        self.send_type(T_EXIT)
        drained = self.pump(EXIT_DRAIN)
        if drained:
            warn(f"退出过程中收到 {len(drained)} 个残余帧，已丢弃（§14.4 第 4 步）")
        ok("已发 EXIT_CONTROL 并排空，模式应回到 PASSTHROUGH")
        return drained


# ============================================================================
# 帧打印
# ============================================================================

def print_pong(frame: Frame) -> None:
    p = frame.payload
    if len(p) < 4:
        fail(f"PONG PAYLOAD 长度异常：{len(p)}（§12.2 应为 4）")
        return
    mode = "CONTROL" if p[1] == 1 else "PASSTHROUGH"
    ok(f"PONG tag=0x{p[0]:02X} mode={p[1]}({mode}) version=0x{p[2]:02X} reserved=0x{p[3]:02X}")
    if p[2] != PROTO_VERSION:
        warn(f"协议版本不一致：控制器 0x{p[2]:02X}，本工具 0x{PROTO_VERSION:02X}（§12.3）")
    if p[3] != 0:
        warn("reserved 应为 0x00（§12.2）")


def print_kbd_state(frame: Frame) -> None:
    p = frame.payload
    if len(p) < 1:
        fail("REPORT_KEYBOARD_STATE PAYLOAD 为空（§11.3 应为 1 字节）")
        return
    v = p[0]
    flags = (f"valid={bool(v & 0x80)} Num={bool(v & 0x01)} Caps={bool(v & 0x02)} "
             f"Scroll={bool(v & 0x04)} Compose={bool(v & 0x08)} Kana={bool(v & 0x10)}")
    ok(f"REPORT_KEYBOARD_STATE=0x{v:02X} {flags}")
    if v & 0x60:
        warn("bit5/bit6 应为 0（§11.3）")
    if not (v & 0x80):
        info("valid=0：目标机尚未下发 SET_REPORT（§11.4，BIOS 常见，不是故障）")


def print_stats(parser: Parser) -> None:
    info(f"统计：丢弃非帧字节 {parser.skipped}；坏 FNV {parser.bad_fnv}；"
         f"未匹配帧 {len(parser.stray)}")


# ============================================================================
# 文本输入：ASCII -> HID Usage ID（US 布局，§8.3 由上位机负责键码）
# ============================================================================

SHIFT_MOD = 0x02


def _build_text_map() -> dict:
    m: dict[str, tuple[int, bool]] = {}
    for i in range(26):
        m[chr(ord("a") + i)] = (0x04 + i, False)
        m[chr(ord("A") + i)] = (0x04 + i, True)
    for i, ch in enumerate("1234567890"):
        m[ch] = (0x1E + i, False)
    for i, ch in enumerate("!@#$%^&*()"):
        m[ch] = (0x1E + i, True)
    pairs = [
        (" ", 0x2C, False), ("-", 0x2D, False), ("_", 0x2D, True),
        ("=", 0x2E, False), ("+", 0x2E, True), ("[", 0x2F, False), ("{", 0x2F, True),
        ("]", 0x30, False), ("}", 0x30, True), ("\\", 0x31, False), ("|", 0x31, True),
        (";", 0x33, False), (":", 0x33, True), ("'", 0x34, False), ('"', 0x34, True),
        ("`", 0x35, False), ("~", 0x35, True), (",", 0x36, False), ("<", 0x36, True),
        (".", 0x37, False), (">", 0x37, True), ("/", 0x38, False), ("?", 0x38, True),
        ("\n", 0x28, False), ("\r", 0x28, False),          # Enter
        ("\t", 0x2B, False),                               # Tab
        ("\b", 0x2A, False),                               # Backspace
    ]
    for ch, usage, shift in pairs:
        m[ch] = (usage, shift)
    return m


TEXT_MAP = _build_text_map()


def type_text(port: KvmPort, text: str, hold: float = 0.02) -> None:
    """逐字符：按下 -> hold -> 释放（只动 Modifier 与一个键码，避免卡键）"""
    sent = 0
    for ch in text:
        entry = TEXT_MAP.get(ch)
        if entry is None:
            warn(f"US 布局无此字符，跳过：{ch!r}")
            continue
        usage, shift = entry
        port.keyboard(SHIFT_MOD if shift else 0, [usage])
        time.sleep(hold)
        port.keyboard(0, ())
        time.sleep(hold)
        sent += 1
    ok(f"已输入 {sent}/{len(text)} 个字符")


# ============================================================================
# selfcheck：纯逻辑自检（不打开串口）
# ============================================================================

def cmd_selfcheck(_args: argparse.Namespace) -> bool:
    c = Checker("上位机自检（不打开串口）")

    # 1) FNV-1a-32 标准测试向量
    h0 = fnv1a32(b"")
    c.check(h0 == 0x811C9DC5, 'FNV-1a-32("") = 0x811C9DC5', f"实际 0x{h0:08X}")
    h1 = fnv1a32(b"a")
    c.check(h1 == 0xE40C292C, 'FNV-1a-32("a") = 0xE40C292C', f"实际 0x{h1:08X}")

    # 2) 与固件实测字节逐字节对拍（2026-11-01 COM5 抓到的 PONG）
    pong = build_frame(T_PONG, bytes([0x11, 0x01, 0x01, 0x00]))
    expect_pong = "4B 56 4D 00 A5 5A C3 3C 01 21 04 00 11 01 01 00 9C 19 A5 D7"
    c.check(hexs(pong) == expect_pong, "PONG 帧与固件实测字节一致", hexs(pong))

    # 3) 解析器往返
    p = Parser()
    p.feed(pong)
    frames = p.pop_frames()
    c.check(len(frames) == 1 and frames[0].type == T_PONG
            and hexs(frames[0].payload) == "11 01 01 00" and not p.buf,
            "解析器往返：PONG 解出 tag/mode/version/reserved", f"帧数={len(frames)}")

    # 4) 日志噪声 + 完整帧 + 尾部半帧
    noise = b"I (401776) kvm: pong sent: tag=0x11\r\n"
    p = Parser()
    p.feed(noise + pong + MAGIC[:3])
    frames = p.pop_frames()
    c.check(len(frames) == 1 and len(p.buf) == 3 and p.skipped >= len(noise),
            "噪声跳过 + 帧解出 + 半帧保留待续",
            f"skipped={p.skipped} 残留={len(p.buf)}")

    # 5) 坏 FNV 必须能重同步到下一帧
    bad = bytearray(pong)
    bad[-1] ^= 0xFF
    p = Parser()
    p.feed(bytes(bad) + pong)
    frames = p.pop_frames()
    c.check(len(frames) == 1 and p.bad_fnv >= 1,
            "坏 FNV 被丢弃且重同步成功（§13.3 前移 1 字节）",
            f"bad_fnv={p.bad_fnv} 帧数={len(frames)}")

    # 6) LENGTH > MAX_PAYLOAD 按 A 类处理（§15.1）
    oversize = MAGIC + bytes([PROTO_VERSION, T_PING, 0xD0, 0x07])   # LENGTH=2000
    p = Parser()
    p.feed(oversize + pong)
    frames = p.pop_frames()
    c.check(len(frames) == 1 and p.skipped >= 1,
            "LENGTH > 1024 被判 A 类并重同步", f"skipped={p.skipped}")

    # 7) VERSION 不认识按 A 类处理（§15.1）
    bad_version = MAGIC + bytes([0x09, T_PING, 0x01, 0x00, 0x00])
    p = Parser()
    p.feed(bad_version + pong)
    frames = p.pop_frames()
    c.check(len(frames) == 1 and p.skipped >= 1,
            "VERSION≠0x01 被判 A 类并重同步", f"skipped={p.skipped}")

    # 8) 协议长度表（§6）
    c.check(all(payload_len(t) == n for t, n in PAYLOAD_LEN.items())
            and payload_len(0x55) == -1, "PAYLOAD 长度表与 §6 一致")

    # 9) 键盘 8 字节报告布局：Modifier + Reserved + 6 Keycode
    kb = build_frame(T_KEYBOARD, bytes([0x02, 0x00, 0x04, 0, 0, 0, 0, 0]))
    c.check(len(kb) == 24 and kb[10] == 8 and kb[12] == 0x02 and kb[14] == 0x04,
            "KEYBOARD 帧：总长 24 / LENGTH=8 / 修饰键与键码位置正确")

    # 10) 绝对坐标小端
    ab = build_frame(T_MOUSE_ABS, bytes([0x00, 0xFF, 0x3F, 0xFF, 0x3F, 0x00]))
    c.check(ab[10] == 6 and ab[13] == 0xFF and ab[14] == 0x3F,
            "MOUSE_ABS：16383 -> FF 3F（小端）")

    # 11) US 布局映射抽查
    c.check(TEXT_MAP["a"] == (0x04, False) and TEXT_MAP["A"] == (0x04, True)
            and TEXT_MAP["!"] == (0x1E, True) and TEXT_MAP[" "] == (0x2C, False)
            and len(TEXT_MAP) == 99,
            "US 布局映射抽查（a/A/!/空格，共 99 项）", f"条目={len(TEXT_MAP)}")

    # 12) int8 二补码 / 坐标小端 / 范围校验
    c.check(to_byte(-1, "t") == 0xFF and to_byte(-128, "t") == 0x80
            and to_abs16(32767, "t") == b"\xFF\x7F" and to_abs16(0, "t") == b"\x00\x00",
            "int8 二补码与坐标小端转换")
    raised = False
    try:
        to_abs16(32768, "X")
    except ValueError:
        raised = True
    c.check(raised, "越界坐标被拒绝（§10.2 上位机负责校验）")

    # 13) 反射自检：源码里所有 port.<成员> 调用点必须在 KvmPort 上真实存在
    #     （防止拆分编辑漏写方法，直到跑某个命令才 AttributeError）
    port_attrs = set()
    known = set(dir(KvmPort))
    with open(__file__, "r", encoding="utf-8") as fp:
        tree = ast.parse(fp.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "port":
                port_attrs.add(node.attr)
            elif node.value.id == "self" and isinstance(node.ctx, ast.Store):
                known.add(node.attr)      # 实例属性（如 __init__ 里赋值的 parser）
    missing = sorted(a for a in port_attrs if a not in known)
    c.check(not missing, f"命令用到的 {len(port_attrs)} 个 KvmPort 成员全部已实现",
            "缺失：" + ", ".join(missing))

    return c.summary()


# ============================================================================
# 命令实现
# ============================================================================

def cmd_monitor(port: KvmPort, args: argparse.Namespace) -> bool:
    step(f"监听 {args.seconds:g} 秒（只解码，不改模式）")
    info("现在可以在另一端发帧，观察解码结果与丢弃计数")
    count = 0
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        window = min(0.05, max(0.0, deadline - time.monotonic()))
        for f in port.pump(window):
            count += 1
            info(f"RX  {f}")
    ok(f"解出 {count} 帧；丢弃非帧字节 {port.parser.skipped}；坏 FNV {port.parser.bad_fnv}")
    return True


def cmd_status(port: KvmPort, args: argparse.Namespace) -> bool:
    step("同步到 CONTROL（§14.1）")
    if not port.sync_control(args.tag):
        fail("同步失败：控制器可能已复位（§14.5）")
        return False
    step("查询键盘状态（§11.2）")
    st = port.query()
    if st is None:
        fail("QUERY 超时（§14.5）")
        return False
    print_kbd_state(st)
    info("status 不退出 CONTROL；要恢复透传请执行 exit")
    return True


def cmd_enter(port: KvmPort, args: argparse.Namespace) -> bool:
    if not port.sync_control(args.tag):
        fail("同步失败（§14.5：检查串口 / 控制器是否刚被复位）")
        return False
    info("现在处于 CONTROL 模式；用完请执行 exit 恢复透传")
    return True


def cmd_exit(port: KvmPort, args: argparse.Namespace) -> bool:
    port.exit_control()
    return True


def cmd_reset(port: KvmPort, args: argparse.Namespace) -> bool:
    """按 §14.6 发送 RESET，并用"PING 是否静默"判定是否真的重启了"""
    if not port.sync_control(args.tag):
        fail("同步失败，未发送 RESET（§14.6 第 1 步）")
        return False

    step("发送 RESET（0x03，PAYLOAD 0，无应答，§4.5）")
    port.send_type(T_RESET)
    info(f"等待 {RESET_SETTLE:.1f} s（芯片重启 + USB 重新枚举）")
    time.sleep(RESET_SETTLE)

    step("判定：复位后模式回 PASSTHROUGH，PING 应静默超时（§14.6 第 4 步）")
    pong = port.ping(args.tag, show=False)
    if pong is not None:
        mode = pong.payload[1] if len(pong.payload) >= 2 else -1
        fail(f"PING 仍返回 mode={mode} → 设备没有重启（固件可能不支持 RESET）")
        return False
    ok("PING 无响应 → 设备确实重启了（已回到 PASSTHROUGH）")

    step("重新同步到 CONTROL（§14.1）")
    for attempt in range(1, RESET_SYNC_RETRIES + 1):
        if port.sync_control(args.tag):
            ok(f"RESET 完成：设备已重启并重新进入 CONTROL（第 {attempt} 次）")
            return True
        warn(f"第 {attempt} 次重新同步失败，{RESET_SYNC_DELAY:.1f} s 后重试")
        time.sleep(RESET_SYNC_DELAY)
    fail("复位后重新同步失败：请检查串口与固件")
    return False


def cmd_ping(port: KvmPort, args: argparse.Namespace) -> bool:
    pong = port.ping(args.tag)
    if pong is None:
        fail("PING 超时（PASSTHROUGH 下静默属正常，§12.4；先 enter）")
        return False
    print_pong(pong)
    return True


def cmd_query(port: KvmPort, args: argparse.Namespace) -> bool:
    if not args.no_sync and not port.sync_control(args.tag):
        fail("同步失败，未发送 QUERY")
        return False
    st = port.query()
    if st is None:
        fail("QUERY 超时（§14.5）")
        return False
    print_kbd_state(st)
    return True


def cmd_key(port: KvmPort, args: argparse.Namespace) -> bool:
    # 参数先校验，再决定是否同步：避免"参数错却已经把模式切到 CONTROL"
    if args.hold_ms < 0:
        raise ValueError("--hold-ms 不能为负")
    modifier, key = args.modifier, args.key
    if not args.no_sync and not port.sync_control(args.tag):
        fail("同步失败，未发送键盘报告")
        return False
    if args.action in ("down", "press"):
        port.keyboard(modifier, [key])
    if args.action == "press":
        time.sleep(args.hold_ms / 1000.0)
    if args.action in ("up", "press"):
        port.keyboard(0, ())
    ok(f"键盘完成：mod=0x{modifier:02X} key=0x{key:02X} action={args.action}")
    return True


def cmd_text(port: KvmPort, args: argparse.Namespace) -> bool:
    if not args.text:
        raise ValueError('text 命令需要文本参数，例如：text "hello"')
    if not args.no_sync and not port.sync_control(args.tag):
        fail("同步失败，未输入文本")
        return False
    type_text(port, args.text)
    return True


def cmd_mrel(port: KvmPort, args: argparse.Namespace) -> bool:
    to_byte(args.buttons, "Buttons")
    to_byte(args.dx, "Dx")
    to_byte(args.dy, "Dy")
    to_byte(args.wheel, "Wheel")
    if not args.no_sync and not port.sync_control(args.tag):
        fail("同步失败，未发送鼠标报告")
        return False
    port.mouse_rel(args.buttons, args.dx, args.dy, args.wheel)
    ok(f"相对鼠标已发送：btn=0x{args.buttons:02X} dx={args.dx} dy={args.dy} wheel={args.wheel}")
    return True


def cmd_mabs(port: KvmPort, args: argparse.Namespace) -> bool:
    to_byte(args.buttons, "Buttons")
    to_abs16(args.x, "X")
    to_abs16(args.y, "Y")
    to_byte(args.wheel, "Wheel")
    if not args.no_sync and not port.sync_control(args.tag):
        fail("同步失败，未发送鼠标报告")
        return False
    port.mouse_abs(args.buttons, args.x, args.y, args.wheel)
    ok(f"绝对鼠标已发送：btn=0x{args.buttons:02X} x={args.x} y={args.y} wheel={args.wheel}")
    return True


def cmd_demo(port: KvmPort, args: argparse.Namespace) -> bool:
    """正向流程：每一步都要人眼确认，停留统一 2000 ms"""
    info("前提：① 目标机已打开 CDC 串口；② 目标机屏幕上开着记事本并已点入光标")
    input("按回车开始...")

    step("1/8 同步到 CONTROL")
    if not port.sync_control(args.tag):
        fail("同步失败，中止（§14.5）")
        return False

    step("2/8 查询键盘状态（间隔 200 ms，共 3 次，§11.6）")
    for i in range(3):
        st = port.query()
        if st is None:
            fail(f"第 {i + 1} 次 QUERY 超时")
        else:
            print_kbd_state(st)
        if i < 2:
            time.sleep(QUERY_INTERVAL)

    step("3/8 键盘：按下 a 再释放（目标机记事本应出现一个 a）")
    port.keyboard(0, [0x04])
    time.sleep(args.hold_ms / 1000.0)
    port.keyboard(0, ())
    time.sleep(HUMAN_OBSERVE)

    step("4/8 相对鼠标：+30/+30，再 -30/-30 回原位")
    port.mouse_rel(0, 30, 30, 0)
    time.sleep(HUMAN_OBSERVE)
    port.mouse_rel(0, -30, -30, 0)
    time.sleep(0.5)

    step("5/8 绝对鼠标：瞬移到屏幕正中（16383,16383，§10.1）")
    port.mouse_abs(0, 16383, 16383, 0)
    time.sleep(HUMAN_OBSERVE)

    step("6/8 绝对鼠标滚轮：+1 再 -1（§10 第 6 字节）")
    port.mouse_abs(0, 16383, 16383, 1)
    time.sleep(HUMAN_OBSERVE)
    port.mouse_abs(0, 16383, 16383, -1)
    time.sleep(HUMAN_OBSERVE)

    step("7/8 安全退出到 PASSTHROUGH（§14.4）")
    port.exit_control()

    step('8/8 透传验证：发送 ASCII "PASS-A"')
    port.write(b"PASS-A\r\n", label="ASCII 文本")
    time.sleep(HUMAN_OBSERVE)
    info("目标机串口窗口应显示 PASS-A；COM5 侧不应出现这些字节（第 10 条）")

    print()
    print_stats(port.parser)
    print()
    info("人工核对清单：")
    info("  [ ] 2/8 每次 QUERY 都返回 REPORT_KEYBOARD_STATE")
    info("  [ ] 3/8 记事本出现 a")
    info("  [ ] 4/8 光标右下移动后回到原位")
    info("  [ ] 5/8 光标瞬移到屏幕正中")
    info("  [ ] 6/8 窗口滚动一格后再滚回")
    info("  [ ] 8/8 目标机串口窗口出现 PASS-A")
    return True


def cmd_test(port: KvmPort, args: argparse.Namespace) -> bool:
    """异常用例：A/B 类失败、模式边界、幂等（§4.3 / §12.4 / §15）"""
    c = Checker("异常用例（A/B 类失败、模式边界、幂等）")
    info("本用例会切换模式并发坏帧；除第 6 步外不会驱动目标机键鼠")
    input("按回车开始...")

    step("0) 基线：EXIT 后应处于 PASSTHROUGH")
    port.exit_control()
    time.sleep(0.2)
    c.check(port.ping((args.tag + 0) & 0xFF) is None, "PASSTHROUGH 下 PING 静默（§12.4）")
    c.check(port.query() is None, "PASSTHROUGH 下 QUERY 静默（§11.2）")

    step("1) 进入 CONTROL")
    c.check(port.sync_control((args.tag + 1) & 0xFF),
            "ENTER_CONTROL 之后 PING 报告 mode=1")

    step("2) A 类：半帧后停 150 ms（帧内超时 100 ms，§13.5）")
    port.write(MAGIC + bytes([PROTO_VERSION, T_PING, 0x01, 0x00]),
               label="半帧（缺 PAYLOAD 与校验）")
    time.sleep(0.15)
    c.check(len(port.pump(0.1)) == 0, "半帧不产生任何响应帧")
    c.check(port.ping((args.tag + 2) & 0xFF) is not None,
            "半帧超时后解析器未卡死，PING 仍正常")

    step("3) A 类：坏 FNV 的 PING（§15.1）")
    bad = bytearray(build_frame(T_PING, bytes([(args.tag + 3) & 0xFF])))
    bad[-1] ^= 0xFF
    port.write(bytes(bad), label="坏 FNV（末字节取反）")
    c.check(len(port.pump(0.2)) == 0, "坏帧不产生 PONG")
    c.check(port.ping((args.tag + 4) & 0xFF) is not None,
            "坏帧之后仍能正常 PING（重同步成功）")

    step("4) A 类：LENGTH > 1024（§15.1）")
    port.write(MAGIC + bytes([PROTO_VERSION, T_PING, 0xD0, 0x07, 0x00]), label="LENGTH=2000")
    c.check(len(port.pump(0.2)) == 0, "超长 LENGTH 不产生响应")
    c.check(port.ping((args.tag + 5) & 0xFF) is not None,
            "超长头部之后仍能正常 PING")

    step("5) B 类：未知 TYPE 0x55（§15.2）")
    port.send_type(0x55, bytes([0x01, 0x02]))
    c.check(len(port.pump(0.15)) == 0, "未知 TYPE 整帧丢弃，不回复")
    c.check(port.ping((args.tag + 6) & 0xFF) is not None,
            "未知 TYPE 之后仍能正常 PING")

    step("6) B 类：CONTROL 下 KEYBOARD 长度错（7 字节，§15.2）")
    port.send_type(T_KEYBOARD, bytes([0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00]))
    c.check(len(port.pump(0.15)) == 0, "长度不符的 KEYBOARD 被丢弃，目标机不应出现字符")
    c.check(port.ping((args.tag + 7) & 0xFF) is not None,
            "长度错的键盘帧之后仍能正常 PING")

    step("7) ENTER 幂等（§4.3）")
    port.send_type(T_ENTER)
    time.sleep(SYNC_SETTLE)
    pong = port.ping((args.tag + 8) & 0xFF)
    c.check(pong is not None and len(pong.payload) >= 2 and pong.payload[1] == 1,
            "重复 ENTER 无副作用，仍为 CONTROL")

    step("8) EXIT 后 PING 静默 + 透传恢复（§12.4 / §14.4）")
    port.exit_control()
    c.check(port.ping((args.tag + 9) & 0xFF) is None,
            "EXIT 之后 PING 无响应（已回 PASSTHROUGH）")
    port.write(b"PASS-B\r\n", label="ASCII 文本")
    time.sleep(0.3)
    info("目标机串口窗口应出现 PASS-B（透传已恢复）")

    print()
    print_stats(port.parser)
    return c.summary()


COMMANDS: dict[str, Callable[[KvmPort, argparse.Namespace], bool]] = {
    "monitor": cmd_monitor,
    "status": cmd_status,
    "enter": cmd_enter,
    "exit": cmd_exit,
    "reset": cmd_reset,
    "ping": cmd_ping,
    "query": cmd_query,
    "key": cmd_key,
    "text": cmd_text,
    "mrel": cmd_mrel,
    "mabs": cmd_mabs,
    "demo": cmd_demo,
    "test": cmd_test,
}


# ============================================================================
# 命令行
# ============================================================================

def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kvm_client.py",
        description="KVM 控制器上位机联调客户端（docs/PROTOCOL.md v1.4）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python tools/kvm_client.py selfcheck
  python tools/kvm_client.py monitor -n 10
  python tools/kvm_client.py status
  python tools/kvm_client.py key --modifier 0x02 --key 0x04
  python tools/kvm_client.py text "hello"
  python tools/kvm_client.py mabs --x 0 --y 0
  python tools/kvm_client.py demo
  python tools/kvm_client.py test
  python tools/kvm_client.py reset

注意：DTR/RTS 都不会被拉高；key/text/mrel/mabs/query 默认先同步到 CONTROL，
      恢复透传请执行 exit（§14.4）。reset 会重启控制器，目标机 USB 会重新枚举（§4.5）。""",
    )
    parser.add_argument("--port", default="COM5", help="串口名（默认 COM5 = CH343 UART）")
    parser.add_argument("--baud", type=int, default=115200, help="波特率（协议固定 115200）")
    parser.add_argument("--tag", type=lambda s: int(s, 0), default=0x11,
                        help="PING tag（默认 0x11）")
    parser.add_argument("--no-sync", action="store_true", help="跳过 CONTROL 同步（§14.1）")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("selfcheck", help="纯逻辑自检（不打开串口）")

    sp = sub.add_parser("monitor", help="只接收并解码")
    sp.add_argument("-n", "--seconds", type=float, default=10.0, help="监听秒数（默认 10）")

    sub.add_parser("status", help="同步到 CONTROL 后查 PONG + 键盘状态")
    sub.add_parser("enter", help="同步到 CONTROL")
    sub.add_parser("exit", help="安全退出到 PASSTHROUGH")
    sub.add_parser("reset", help="重启控制器（§4.5；目标机 USB 会重新枚举）")
    sub.add_parser("ping", help="发 PING 等 PONG")
    sub.add_parser("query", help="发 QUERY 等 REPORT_KEYBOARD_STATE")

    sp = sub.add_parser("key", help="发一次键盘报告")
    sp.add_argument("--modifier", type=lambda s: int(s, 0), default=0x00, help="修饰键位图")
    sp.add_argument("--key", type=lambda s: int(s, 0), default=0x04, help="HID Usage ID")
    sp.add_argument("--action", choices=["press", "down", "up"], default="press")
    sp.add_argument("--hold-ms", type=int, default=80, help="按下保持毫秒数")

    sp = sub.add_parser("text", help="逐字符输入 ASCII 文本（US 布局）")
    sp.add_argument("text", help="要输入的文本")

    sp = sub.add_parser("mrel", help="相对鼠标")
    sp.add_argument("--buttons", type=lambda s: int(s, 0), default=0)
    sp.add_argument("--dx", type=int, default=0)
    sp.add_argument("--dy", type=int, default=0, help="下为正")
    sp.add_argument("--wheel", type=int, default=0, help="上滚为正")

    sp = sub.add_parser("mabs", help="绝对鼠标（0~32767）")
    sp.add_argument("--buttons", type=lambda s: int(s, 0), default=0)
    sp.add_argument("--x", type=int, default=16383)
    sp.add_argument("--y", type=int, default=16383)
    sp.add_argument("--wheel", type=int, default=0)

    sp = sub.add_parser("demo", help="正向用例（人工观察，约 25 s）")
    sp.add_argument("--hold-ms", type=int, default=80)

    sub.add_parser("test", help="异常用例")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    # 不强制 UTF-8：中文 Windows 控制台/重定向用本地代码页（cp936）显示中文最稳
    args = build_argparser().parse_args(argv)

    if args.cmd == "selfcheck":
        return 0 if cmd_selfcheck(args) else 1

    print(f"\n=== 打开串口 {args.port} @ {args.baud} 8N1 ===")
    try:
        port = KvmPort(args.port, args.baud)
    except serial.SerialException as exc:
        fail(f"无法打开串口 {args.port}：{exc}")
        info("常见原因：idf.py monitor 或其他串口工具正占用该端口")
        return 1

    ok("串口已打开（DTR/RTS 均未拉高）")
    try:
        success = COMMANDS[args.cmd](port, args)
        if port.parser.skipped or port.parser.bad_fnv or port.parser.stray:
            print()
            print_stats(port.parser)
        return 0 if success else 1
    except ValueError as exc:
        fail(f"参数错误：{exc}")
        return 1
    except serial.SerialException as exc:
        fail(f"串口读写失败：{exc}")
        return 1
    except KeyboardInterrupt:
        warn("用户中断，尝试释放全部键位并退出 CONTROL（§14.4）")
        try:
            port.exit_control()
        except Exception:
            pass
        return 1
    finally:
        port.close()


if __name__ == "__main__":
    sys.exit(main())