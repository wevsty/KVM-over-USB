"""
ESP32-S3 KVM 控制器上位机驱动（协议 v1.4）。
"""

import threading
import time
import typing
from enum import IntEnum

from loguru import logger
from serial import SerialException

from controller.base import ControllerDeviceBase
from controller.serial_device import SerialDevice
from keyboard_buffer import KeyboardKeyBuffer, KeyStateEnum
from mouse_buffer import (
    MouseButtonCodeEnum,
    MouseButtonStateEnum,
    MouseStateBuffer,
    MouseWheelStateEnum,
)


class KvmCommand(IntEnum):
    """协议 §6 的 TYPE 总表"""

    ENTER_CONTROL = 0x01
    EXIT_CONTROL = 0x02
    RESET = 0x03
    KEYBOARD = 0x10
    MOUSE_RELATIVE = 0x11
    MOUSE_ABSOLUTE = 0x12
    REPORT_KEYBOARD_STATE = 0x13
    QUERY_KEYBOARD_STATE = 0x14
    PING = 0x20
    PONG = 0x21


class KvmProtocol:
    """KVM 协议封装：常量、组帧（发送）与流式解帧（接收）。

    协议常量全部是本类的类属性，模块级不再有 MAGIC / VERSION 之类的散落常量；
    实例只保存"当前待发送的命令"和"接收滑窗"，因此同一个实例可同时收发。
    """

    # ---- 物理层（§2）----
    BAUD_RATE: typing.Final[int] = 115200

    # ---- 帧格式（§5.1 / §5.3）----
    MAGIC: typing.Final[bytes] = b"\x4b\x56\x4d\x00\xa5\x5a\xc3\x3c"
    VERSION: typing.Final[int] = 0x01
    HEADER_LEN: typing.Final[int] = 12
    CHECK_LEN: typing.Final[int] = 4
    MAX_PAYLOAD: typing.Final[int] = 1024
    MAX_FRAME: typing.Final[int] = HEADER_LEN + MAX_PAYLOAD
    OFFSET_VERSION: typing.Final[int] = 8
    OFFSET_COMMAND: typing.Final[int] = 9
    OFFSET_LENGTH: typing.Final[int] = 10
    OFFSET_PAYLOAD: typing.Final[int] = 12

    # ---- TYPE -> 固定 PAYLOAD 长度（§6），不在表内即未知 TYPE ----
    PAYLOAD_LENGTH: typing.Final[dict[KvmCommand, int]] = {
        KvmCommand.ENTER_CONTROL: 0,
        KvmCommand.EXIT_CONTROL: 0,
        KvmCommand.RESET: 0,
        KvmCommand.KEYBOARD: 8,
        KvmCommand.MOUSE_RELATIVE: 4,
        KvmCommand.MOUSE_ABSOLUTE: 6,
        KvmCommand.REPORT_KEYBOARD_STATE: 1,
        KvmCommand.QUERY_KEYBOARD_STATE: 0,
        KvmCommand.PING: 1,
        KvmCommand.PONG: 4,
    }

    # ---- 模式（§4.1，PONG 第 2 字节）----
    MODE_PASSTHROUGH: typing.Final[int] = 0
    MODE_CONTROL: typing.Final[int] = 1

    # ---- 键盘（§8）----
    KEYCODE_SLOTS: typing.Final[int] = 6
    MODIFIER_BASE: typing.Final[int] = 0xE0

    # ---- 鼠标（§9 / §10）----
    RELATIVE_MIN: typing.Final[int] = -128
    RELATIVE_MAX: typing.Final[int] = 127
    ABSOLUTE_MAX: typing.Final[int] = 32767
    WHEEL_UP: typing.Final[int] = 1
    WHEEL_DOWN: typing.Final[int] = -1
    WHEEL_STOP: typing.Final[int] = 0
    BUTTON_LEFT: typing.Final[int] = 0x01
    BUTTON_RIGHT: typing.Final[int] = 0x02
    BUTTON_MIDDLE: typing.Final[int] = 0x04
    BUTTON_BACK: typing.Final[int] = 0x08
    BUTTON_FORWARD: typing.Final[int] = 0x10

    # ---- 键盘状态位（§11.3）----
    STATE_NUM_LOCK: typing.Final[int] = 0x01
    STATE_CAPS_LOCK: typing.Final[int] = 0x02
    STATE_SCROLL_LOCK: typing.Final[int] = 0x04
    STATE_VALID: typing.Final[int] = 0x80

    def __init__(self) -> None:
        # 发送侧：当前配置的待发送命令
        self._command: KvmCommand | None = None
        self._payload: bytes = b""
        # 接收侧：滑窗 + 统计（便于判断链路噪声）
        self._buffer: bytearray = bytearray()
        self.discarded_bytes: int = 0
        self.bad_fnv_frames: int = 0
        self.rejected_frames: int = 0

    # ------------------------------------------------------------------
    # 发送侧：调用命令方法配置 -> 统一 pack()
    # ------------------------------------------------------------------
    def enter_control(self) -> "KvmProtocol":
        """§4.3：切到 CONTROL（幂等），无响应"""
        return self._configure(KvmCommand.ENTER_CONTROL)

    def exit_control(self) -> "KvmProtocol":
        """§4.3：切回 PASSTHROUGH，无响应"""
        return self._configure(KvmCommand.EXIT_CONTROL)

    def reset(self) -> "KvmProtocol":
        """§4.5：整机重启（仅 CONTROL 生效），无响应"""
        return self._configure(KvmCommand.RESET)

    def keyboard(
        self, modifier: int, keycodes: typing.Sequence[int]
    ) -> "KvmProtocol":
        """§8：modifier 位图 + 最多 6 个 HID Usage ID（不足补 0）"""
        slots: list[int] = [0] * self.KEYCODE_SLOTS
        for index, code in enumerate(keycodes[: self.KEYCODE_SLOTS]):
            slots[index] = int(code) & 0xFF
        payload: bytes = bytes((int(modifier) & 0xFF, 0x00)) + bytes(slots)
        return self._configure(KvmCommand.KEYBOARD, payload)

    def mouse_relative(
        self, buttons: int, dx: int, dy: int, wheel: int
    ) -> "KvmProtocol":
        """§9：dx 右为正、dy 下为正、wheel 上为正（int8 自动截断）"""
        payload: bytes = bytes(
            (
                int(buttons) & 0xFF,
                self.clamp_relative(dx) & 0xFF,
                self.clamp_relative(dy) & 0xFF,
                int(wheel) & 0xFF,
            )
        )
        return self._configure(KvmCommand.MOUSE_RELATIVE, payload)

    def mouse_absolute(
        self, buttons: int, x: int, y: int, wheel: int
    ) -> "KvmProtocol":
        """§10：x / y 为 0~32767（越界自动截断）"""
        payload: bytes = bytes((int(buttons) & 0xFF,))
        payload += self.clamp_absolute(x).to_bytes(2, "little")
        payload += self.clamp_absolute(y).to_bytes(2, "little")
        payload += bytes((int(wheel) & 0xFF,))
        return self._configure(KvmCommand.MOUSE_ABSOLUTE, payload)

    def query_keyboard_state(self) -> "KvmProtocol":
        """§11.2：查询目标机键盘指示灯（仅 CONTROL 有效）"""
        return self._configure(KvmCommand.QUERY_KEYBOARD_STATE)

    def ping(self, tag: int) -> "KvmProtocol":
        """§12.1：存活 / 模式探测，tag 占 1 字节"""
        return self._configure(KvmCommand.PING, bytes((int(tag) & 0xFF,)))

    def pack(self) -> bytes:
        """把当前配置的命令打成完整帧（16 + N 字节，§5.1）"""
        if self._command is None:
            raise RuntimeError("no command configured")
        expected: int | None = self.PAYLOAD_LENGTH.get(self._command)
        if expected != len(self._payload):
            raise ValueError(
                f"{self._command.name} payload must be {expected} bytes, "
                f"got {len(self._payload)}"
            )
        body: bytes = (
            bytes((self.VERSION, int(self._command)))
            + len(self._payload).to_bytes(2, "little")
            + self._payload
        )
        checksum: bytes = self.fnv1a32(body).to_bytes(4, "little")
        return self.MAGIC + body + checksum

    def _configure(
        self, command: KvmCommand, payload: bytes = b""
    ) -> "KvmProtocol":
        self._command = command
        self._payload = payload
        return self

    # ------------------------------------------------------------------
    # 协议数值换算（上层直接用，不再自己算位与范围）
    # ------------------------------------------------------------------
    @staticmethod
    def fnv1a32(data: bytes) -> int:
        """FNV-1a-32（§7.1）"""
        value: int = 0x811C9DC5
        for byte in data:
            value = ((value ^ byte) * 0x01000193) & 0xFFFFFFFF
        return value

    @classmethod
    def clamp_relative(cls, value: float) -> int:
        """§9：位移截断到 int8 范围"""
        return max(cls.RELATIVE_MIN, min(cls.RELATIVE_MAX, int(value)))

    @classmethod
    def clamp_absolute(cls, value: float) -> int:
        """§10.1：绝对坐标截断到 0~32767"""
        return max(0, min(cls.ABSOLUTE_MAX, int(round(float(value)))))

    @classmethod
    def normalize_absolute(cls, ratio: float) -> int:
        """归一化坐标 0.0~1.0 -> 协议绝对坐标 0~32767"""
        return cls.clamp_absolute(float(ratio) * cls.ABSOLUTE_MAX)

    @classmethod
    def modifier_bit(cls, hid_code: int) -> int | None:
        """§8.1：HID Usage 0xE0~0xE7 -> modifier 位；普通键返回 None"""
        offset: int = int(hid_code) - cls.MODIFIER_BASE
        if 0 <= offset <= 7:
            return 1 << offset
        return None

    # ------------------------------------------------------------------
    # 接收侧：feed() -> KvmMessage 列表
    # ------------------------------------------------------------------
    def clear_buffer(self) -> None:
        """丢弃滑窗里尚未成形的半帧"""
        self._buffer.clear()

    def feed(self, data: bytes) -> list["KvmMessage"]:
        """喂入字节流，返回本次解出的完整消息（§13.3 / §13.4）。

        固件日志与协议帧在串口上混流，所以必须逐字节扫描 MAGIC：
          * MAGIC 前缀失配 -> 已确认非帧的字节整体丢弃后重扫；
          * VERSION / LENGTH / FNV 不合法 -> 前移 1 字节重扫；
          * TYPE 未知或 PAYLOAD 长度不符 -> 整帧丢弃（B 类）。
        """
        self._buffer.extend(data)
        messages: list["KvmMessage"] = list()
        while True:
            available: int = len(self._buffer)
            if available == 0:
                return messages
            matched: int = self._magic_prefix_len(available)
            if matched < len(self.MAGIC):
                if matched == available:
                    return messages  # 全是 MAGIC 前缀，等更多字节
                shift: int = matched if matched > 0 else 1
                self.discarded_bytes += shift
                del self._buffer[:shift]
                continue
            if available < self.HEADER_LEN:
                return messages
            version: int = self._buffer[self.OFFSET_VERSION]
            command_type: int = self._buffer[self.OFFSET_COMMAND]
            payload_length: int = int.from_bytes(
                bytes(self._buffer[self.OFFSET_LENGTH : self.OFFSET_PAYLOAD]),
                "little",
            )
            if version != self.VERSION or payload_length > self.MAX_PAYLOAD:
                self.discarded_bytes += 1
                del self._buffer[:1]
                continue
            payload_end: int = self.OFFSET_PAYLOAD + payload_length
            total: int = payload_end + self.CHECK_LEN
            if available < total:
                return messages
            checksum: int = self.fnv1a32(
                bytes(self._buffer[self.OFFSET_VERSION : payload_end])
            )
            received: int = int.from_bytes(
                bytes(self._buffer[payload_end:total]), "little"
            )
            if checksum != received:
                self.bad_fnv_frames += 1
                del self._buffer[:1]
                continue
            payload: bytes = bytes(
                self._buffer[self.OFFSET_PAYLOAD : payload_end]
            )
            del self._buffer[:total]
            message: KvmMessage | None = self._build_message(
                command_type, payload
            )
            if message is not None:
                messages.append(message)
        return messages

    def unpack(self, data: bytes) -> "KvmMessage | None":
        """一次性解一整帧：正好一帧则返回消息，否则返回 None"""
        self.clear_buffer()
        messages = self.feed(data)
        self.clear_buffer()
        return messages[0] if len(messages) == 1 else None

    def _magic_prefix_len(self, available: int) -> int:
        matched: int = 0
        limit: int = min(available, len(self.MAGIC))
        while matched < limit and self._buffer[matched] == self.MAGIC[matched]:
            matched += 1
        return matched

    def _build_message(
        self, command_type: int, payload: bytes
    ) -> "KvmMessage | None":
        """TYPE 与 PAYLOAD 长度自洽性检查（不符按 §15.2 B 类丢弃）"""
        try:
            command = KvmCommand(command_type)
        except ValueError:
            self.rejected_frames += 1
            logger.debug(f"unknown TYPE dropped: 0x{command_type:02X}")
            return None
        if self.PAYLOAD_LENGTH.get(command) != len(payload):
            self.rejected_frames += 1
            logger.debug(f"{command.name} payload length mismatch, dropped")
            return None
        return KvmMessage(command, payload)


class KvmMessage:
    """一条已解析的协议消息；字段含义由协议类统一解释，不散落在调用方。"""

    def __init__(self, command: KvmCommand, payload: bytes) -> None:
        self.command: KvmCommand = command
        self.payload: bytes = payload

    def __repr__(self) -> str:
        return (
            f"KvmMessage(command={self.command.name}, "
            f"payload={self.payload.hex(' ').upper()})"
        )

    @property
    def tag(self) -> int:
        """PING / PONG 的 tag（§12）"""
        return self.payload[0] if self.payload else 0

    @property
    def mode(self) -> int:
        """PONG 的模式：0 = PASSTHROUGH，1 = CONTROL（§12.2）"""
        return self.payload[1] if len(self.payload) >= 2 else -1

    @property
    def version(self) -> int:
        """PONG 的协议版本（§12.2）"""
        return self.payload[2] if len(self.payload) >= 3 else -1

    @property
    def keyboard_state(self) -> int:
        """REPORT_KEYBOARD_STATE 原始字节（§11.3）"""
        return self.payload[0] if self.payload else 0

    @property
    def keyboard_state_valid(self) -> bool:
        """§11.4：目标机是否下发过 SET_REPORT"""
        return bool(self.keyboard_state & KvmProtocol.STATE_VALID)

    def keyboard_locks(self) -> dict[str, bool]:
        """§11.3：Num / Caps / Scroll 三个锁定指示"""
        state: int = self.keyboard_state
        return {
            "num_lock": bool(state & KvmProtocol.STATE_NUM_LOCK),
            "caps_lock": bool(state & KvmProtocol.STATE_CAPS_LOCK),
            "scroll_lock": bool(state & KvmProtocol.STATE_SCROLL_LOCK),
        }


class ControllerEsp32s3Kvm(ControllerDeviceBase):
    """ESP32-S3 KVM 控制器

    协议细节（组帧、解帧、位定义、范围换算）全部委托 KvmProtocol，
    本类只负责串口、模式机，以及上位机缓冲区（KeyboardKeyBuffer /
    MouseStateBuffer）到协议字段的映射。
    """

    # ---- 时序（协议 §14）----
    RESPONSE_TIMEOUT: typing.Final[float] = 0.1
    SYNC_ENTER_DELAY: typing.Final[float] = 0.02
    SYNC_RETRY_COUNT: typing.Final[int] = 3
    EXIT_DISCARD: typing.Final[float] = 0.1
    PROBE_INTERVAL: typing.Final[float] = 2.0
    POLL_INTERVAL: typing.Final[float] = 0.002

    # ---- RESET 判定（协议 §14.6）----
    # 第 3 步要求等 >= 1 s：芯片重启 + USB 重新枚举 + mount 都要时间
    RESET_SETTLE: typing.Final[float] = 1.0
    # 复位后重新握手前的额外等待（首次尝试不等，只用于重试）
    RESET_RETRY_DELAY: typing.Final[float] = 0.5

    # ---- 上位机缓冲区枚举 -> 协议 §9.1 按键位 ----
    MOUSE_BUTTON_BITS: typing.Final[dict[MouseButtonCodeEnum, int]] = {
        MouseButtonCodeEnum.LEFT_BUTTON: KvmProtocol.BUTTON_LEFT,
        MouseButtonCodeEnum.RIGHT_BUTTON: KvmProtocol.BUTTON_RIGHT,
        MouseButtonCodeEnum.MIDDLE_BUTTON: KvmProtocol.BUTTON_MIDDLE,
        MouseButtonCodeEnum.XBUTTON1_BUTTON: KvmProtocol.BUTTON_BACK,
        MouseButtonCodeEnum.XBUTTON2_BUTTON: KvmProtocol.BUTTON_FORWARD,
    }

    def __init__(self) -> None:
        self.port: str = "auto"
        self.baud_rate: int = KvmProtocol.BAUD_RATE
        self.timeout: float = 0.5
        # 仅记录用：绝对坐标固定 0~32767，与分辨率无关（协议 §10.1）
        self.screen_x: int = 0
        self.screen_y: int = 0
        self.relative_click: bool = False
        # 探活间隔（秒）；<= 0 表示只检查串口是否打开，不发 PING
        self.probe_interval: float = self.PROBE_INTERVAL

        # 实际类型是 serial.Serial；这里用鸭子类型，便于离线测试注入假串口
        self._connection: typing.Any = None
        self._mutex: threading.RLock = threading.RLock()
        self._protocol: KvmProtocol = KvmProtocol()
        self._in_control: bool = False
        self._connection_broken: bool = False
        self._ping_tag: int = 0
        self._last_probe_time: float = 0.0

        # 键盘/鼠标本地状态（固件只认"当前完整报告"）
        self._keyboard_modifier: int = 0
        self._keyboard_keycodes: list[int] = [0] * KvmProtocol.KEYCODE_SLOTS
        self._mouse_buttons: int = 0
        # 绝对坐标释放时要复用最后发送过的坐标，避免光标被拉到左上角
        self._absolute_sent: bool = False
        self._last_absolute_point: tuple[int, int] = (0, 0)

    @property
    def connection(self) -> typing.Any:
        if self._connection is None:
            raise RuntimeError("Connection is not initialized")
        return self._connection

    @connection.setter
    def connection(self, value: typing.Any) -> None:
        self._connection = value

    ######################################################################
    # 设备生命周期
    ######################################################################
    def device_init(self, buffer: typing.Any) -> bool:
        config: dict[str, typing.Any] = buffer
        self.port = str(config.get("port", "auto"))
        configured_baud_rate: int = int(
            config.get("baud_rate", KvmProtocol.BAUD_RATE)
        )
        if configured_baud_rate != KvmProtocol.BAUD_RATE:
            logger.debug(
                "ESP32-S3 KVM 固定使用 "
                f"{KvmProtocol.BAUD_RATE} 波特率，忽略配置值 "
                f"{configured_baud_rate}"
            )
        self.baud_rate = KvmProtocol.BAUD_RATE
        self.timeout = float(config.get("timeout", 0.5))
        self.screen_x = int(config.get("resolution_x", 0) or 0)
        self.screen_y = int(config.get("resolution_y", 0) or 0)
        self.relative_click = bool(config.get("relative_click", False))
        logger.info(
            f"ESP32-S3 KVM controller: port={self.port} "
            f"baud={self.baud_rate} screen={self.screen_x}x{self.screen_y}"
        )
        return True

    def device_open(self) -> bool:
        with self._mutex:
            status, connection = SerialDevice.create_serial_connection(
                self.port, self.baud_rate, self.timeout
            )
            self.connection = connection
            if not status or connection is None:
                logger.error("Open controller serial port failed")
                return False
            self._prepare_line()
            self._protocol.clear_buffer()
            self._reset_input_state()
            self._connection_broken = False
            self._in_control = False
            self._last_probe_time = time.monotonic()
            # 紧接着做 ENTER_CONTROL + PING 同步（协议 §14.1）。
            # 握手失败不阻止"端口已打开"这一事实：首次键鼠/查询时会自动重试，
            # 这样固件刚复位（串口刚打开、还在打 boot 日志）时不会误报失败。
            if not self._sync_control():
                logger.warning(
                    "CONTROL handshake failed, will retry on first input"
                )
            return True

    def device_close(self) -> None:
        with self._mutex:
            if self._is_open():
                # 协议 §14.4：先全释放，再 EXIT_CONTROL，最后丢弃残余响应
                self._release_all()
                self._write(self._protocol.exit_control())
                self._discard_input(self.EXIT_DISCARD)
            SerialDevice.close_serial_connection(self._connection)
            self._connection = None
            self._in_control = False
            self._connection_broken = False
            self._protocol.clear_buffer()
            self._reset_input_state()

    def device_check_connection(self) -> bool:
        with self._mutex:
            if not self._is_open() or self._connection_broken:
                return False
            if self.probe_interval <= 0:
                return True
            now: float = time.monotonic()
            if (now - self._last_probe_time) < self.probe_interval:
                return True
            self._last_probe_time = now
            self._probe_device()
            return not self._connection_broken

    ######################################################################
    # 设备事件（命令名与 ControllerCh9329 完全一致）
    ######################################################################
    def device_event(
        self, command: str, buffer: typing.Any
    ) -> tuple[str, int, typing.Any]:
        status_code: int = self.generate_status_code(True)
        reply: typing.Any = None

        with self._mutex:
            if command == "keyboard_write":
                self.keyboard_send_event(buffer)
            elif command == "keyboard_read":
                status_code, reply = self.keyboard_recv_event(command)
            elif command == "mouse_absolute_write":
                self.mouse_send_event(command, buffer)
            elif command == "mouse_relative_write":
                self.mouse_send_event(command, buffer)
            elif command == "device_reload":
                self.device_release(buffer)
            elif command == "device_reset":
                self.device_reset()
            else:
                logger.debug(f"Unhandled command: {command}")

        return command, status_code, reply

    def device_release(self, device_type: str) -> None:
        known_type = ["mouse", "keyboard", "all", "any"]
        if device_type not in known_type:
            raise ValueError(f"unknown release type: {device_type}")
        self.controller_release(device_type)

    def device_reset(self) -> None:
        """协议 §4.5 RESET：整机重启，然后按 §14.6 判定并重新同步。

        RESET 没有任何响应帧，因此用"复位后 PING 必须静默"来判定
        （复位后模式回到 PASSTHROUGH，而 PASSTHROUGH 下 PING 不响应）。
        若仍收到 PONG(mode=1)，说明固件忽略了 0x03，记警告但不中断流程。
        """
        with self._mutex:
            if not self._is_open():
                return
            # 第 1 步：RESET 仅 CONTROL 生效，否则先按 §14.1 同步
            if not self._ensure_control():
                logger.error("RESET aborted: controller is not in CONTROL")
                return
            # 固件重启会清空键位缓存，先进位全释放避免目标机卡键
            self._release_all()
            # 第 2 步：发送 RESET
            if not self._write(self._protocol.reset()):
                return
            self._in_control = False
            self._protocol.clear_buffer()
            # 第 3~4 步：等 >= 1 s，再 PING 一次判定是否真的重启
            if self._wait_reset_silence():
                logger.info("Controller restarted (PING silent after RESET)")
            else:
                logger.warning(
                    "Controller answered PING after RESET, "
                    "firmware may have ignored 0x03"
                )
            self._reset_input_state()
            # 第 5 步：重新执行 §14.1；重试间隔放宽，覆盖 USB 重新枚举时间
            if self._sync_control(wait=self.RESET_RETRY_DELAY):
                logger.info("Controller re-synced into CONTROL mode")
            else:
                logger.error("Controller re-sync failed after RESET")

    def _wait_reset_silence(self) -> bool:
        """§14.6 第 3~4 步：等待复位完成，PING 无响应即认为确实重启"""
        time.sleep(self.RESET_SETTLE)
        self._flush_input()  # 丢掉 bootloader 上电日志
        return self._ping() is None

    ######################################################################
    # 串口收发（协议字段知识全部在 KvmProtocol 里）
    ######################################################################
    def _is_open(self) -> bool:
        connection = self._connection
        if connection is None:
            return False
        return bool(getattr(connection, "is_open", False))

    def _prepare_line(self) -> None:
        """把 DTR/RTS 置低：避免 CH343 自动下载电路误触发芯片复位"""
        connection = self._connection
        if connection is None:
            return
        try:
            connection.dtr = False
            connection.rts = False
        except (AttributeError, OSError, SerialException) as error:
            logger.debug(f"Set DTR/RTS low failed: {error}")

    def _write(self, protocol: KvmProtocol) -> bool:
        """把已配置好的协议对象 pack() 成二进制帧并写出"""
        if not self._is_open():
            return False
        try:
            frame: bytes = protocol.pack()
            self.connection.write(frame)
            self.connection.flush()
        except (AttributeError, OSError, SerialException) as error:
            logger.error(f"UART write failed: {error}")
            self._connection_broken = True
            return False
        return True

    def _poll_messages(self) -> list[KvmMessage]:
        """把串口当前可读的字节全部交给协议解析器"""
        if not self._is_open():
            return []
        try:
            waiting: int = self.connection.in_waiting
            if waiting <= 0:
                return []
            data: bytes = self.connection.read(waiting)
        except (AttributeError, OSError, SerialException) as error:
            logger.error(f"UART read failed: {error}")
            self._connection_broken = True
            return []
        if not data:
            return []
        return self._protocol.feed(data)

    def _wait_response(
        self,
        expected: KvmCommand,
        timeout: float | None = None,
        matcher: typing.Callable[[KvmMessage], bool] | None = None,
    ) -> KvmMessage | None:
        """在 timeout 内等待指定 TYPE 的响应，其余消息丢弃并记日志"""
        deadline: float = time.monotonic() + (
            self.RESPONSE_TIMEOUT if timeout is None else timeout
        )
        while True:
            for message in self._poll_messages():
                if message.command is not expected:
                    logger.debug(f"unexpected message dropped: {message}")
                    continue
                if matcher is None or matcher(message):
                    return message
                logger.debug(f"response payload mismatch: {message}")
            remaining: float = deadline - time.monotonic()
            if remaining <= 0:
                return None
            time.sleep(min(remaining, self.POLL_INTERVAL))

    def _discard_input(self, duration: float) -> None:
        """按协议 §14.4 第 4 步丢弃残余响应帧"""
        deadline: float = time.monotonic() + duration
        while True:
            remaining: float = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._poll_messages()
            time.sleep(min(remaining, self.POLL_INTERVAL))
        self._protocol.clear_buffer()

    def _flush_input(self) -> None:
        """清掉串口缓冲区里的陈旧字节（复位后的 boot 日志等）"""
        self._protocol.clear_buffer()
        for _ in range(16):
            if not self._poll_messages() and not self._has_pending_bytes():
                break
        self._protocol.clear_buffer()

    def _has_pending_bytes(self) -> bool:
        if not self._is_open():
            return False
        try:
            return int(self.connection.in_waiting) > 0
        except (AttributeError, OSError, SerialException) as error:
            logger.error(f"UART status query failed: {error}")
            self._connection_broken = True
            return False

    ######################################################################
    # 模式握手与探活（协议 §14.1 / §14.5）
    ######################################################################
    def _ping(self, timeout: float | None = None) -> KvmMessage | None:
        self._ping_tag = (self._ping_tag + 1) & 0xFF
        tag: int = self._ping_tag
        if not self._write(self._protocol.ping(tag)):
            return None
        return self._wait_response(
            KvmCommand.PONG, timeout, lambda message: message.tag == tag
        )

    def _sync_control(
        self, attempts: int | None = None, wait: float | None = None
    ) -> bool:
        """ENTER_CONTROL -> 等 20 ms -> PING，失败重试（协议 §14.1）。

        wait 为重试前的额外等待，用于 RESET 后覆盖 USB 重新枚举的时间。
        """
        if not self._is_open():
            return False
        retries: int = self.SYNC_RETRY_COUNT if attempts is None else attempts
        for attempt in range(1, retries + 1):
            if attempt > 1 and wait is not None and wait > 0:
                time.sleep(wait)
            self._flush_input()
            if not self._write(self._protocol.enter_control()):
                return False
            time.sleep(self.SYNC_ENTER_DELAY)
            pong: KvmMessage | None = self._ping()
            if pong is None:
                logger.warning(f"PING timeout (attempt {attempt})")
                continue
            if pong.version != KvmProtocol.VERSION:
                logger.warning(
                    "protocol version mismatch: "
                    f"device={pong.version} upper={KvmProtocol.VERSION}"
                )
            if pong.mode == KvmProtocol.MODE_CONTROL:
                self._in_control = True
                logger.info("Controller entered CONTROL mode")
                return True
            logger.warning(
                f"PING ok but mode={pong.mode} "
                f"(expect {KvmProtocol.MODE_CONTROL}), attempt {attempt}"
            )
        self._in_control = False
        return False

    def _ensure_control(self) -> bool:
        """确保处于 CONTROL 模式；固件复位过会自动重新握手"""
        if not self._is_open():
            return False
        if self._in_control:
            return True
        logger.debug("Controller is not in CONTROL mode, re-syncing")
        return self._sync_control()

    def _probe_device(self) -> None:
        """低频探活：PONG 的 mode 是判断固件是否复位过的唯一手段"""
        if not self._is_open():
            return
        pong: KvmMessage | None = self._ping()
        if pong is None:
            logger.warning("PING timeout, controller may have been reset")
            self._in_control = False
            # 探活路径只重试一次，避免设备长期不在 CONTROL 时反复阻塞
            self._sync_control(attempts=1)
            return
        if pong.mode == KvmProtocol.MODE_CONTROL:
            self._in_control = True
            return
        logger.warning(
            f"Controller left CONTROL (mode={pong.mode}), re-syncing"
        )
        self._in_control = False
        self._sync_control(attempts=1)

    ######################################################################
    # 本地键鼠状态与释放
    ######################################################################
    def _reset_input_state(self) -> None:
        self._keyboard_modifier = 0
        self._keyboard_keycodes = [0] * KvmProtocol.KEYCODE_SLOTS
        self._mouse_buttons = 0
        self._absolute_sent = False
        self._last_absolute_point = (0, 0)

    def _reset_keyboard_state(self) -> None:
        self._keyboard_modifier = 0
        self._keyboard_keycodes = [0] * KvmProtocol.KEYCODE_SLOTS

    def _release_all(self) -> None:
        self.controller_release("all")

    def controller_release(self, release_type: str = "all") -> None:
        """释放按键（协议 §14.4 第 1~2 步）。

        注意：绝对坐标释放必须复用最后发送过的坐标，否则目标机光标
        会被拉到屏幕左上角。
        """
        if not self._is_open() or not self._in_control:
            self._reset_input_state()
            return
        if release_type in ("mouse", "all", "any"):
            self._mouse_buttons = 0
            if self._absolute_sent:
                x, y = self._last_absolute_point
                self._send_mouse_absolute(x, y, KvmProtocol.WHEEL_STOP)
            self._send_mouse_relative(0, 0, KvmProtocol.WHEEL_STOP)
        if release_type in ("keyboard", "all", "any"):
            self._reset_keyboard_state()
            self._send_keyboard_report()
        if release_type not in ("mouse", "keyboard", "all", "any"):
            logger.debug(f"unknown release type: {release_type}")

    ######################################################################
    # 键盘（协议 §8，6KRO Boot 报告）
    ######################################################################
    def keyboard_send_event(self, buffer: KeyboardKeyBuffer) -> None:
        if not self._ensure_control():
            return
        for key in buffer.buffer():
            if key.state == KeyStateEnum.PRESS:
                self._keyboard_press(key.code)
            else:
                self._keyboard_release(key.code)
        self._send_keyboard_report()

    def keyboard_recv_event(self, _command: str) -> tuple[int, dict]:
        return self.keyboard_receive_status()

    def keyboard_receive_status(self) -> tuple[int, dict[str, bool]]:
        """QUERY_KEYBOARD_STATE -> REPORT_KEYBOARD_STATE（协议 §11）"""
        reply: dict[str, bool] = {
            "num_lock": False,
            "caps_lock": False,
            "scroll_lock": False,
        }
        if not self._ensure_control():
            return 1, reply
        if not self._write(self._protocol.query_keyboard_state()):
            return 1, reply
        message: KvmMessage | None = self._wait_response(
            KvmCommand.REPORT_KEYBOARD_STATE
        )
        if message is None:
            logger.debug("Query keyboard state timeout")
            return 1, reply
        if not message.keyboard_state_valid:
            # 协议 §11.4：目标机从未下发 SET_REPORT，状态未知
            logger.debug("Keyboard state invalid (no LED report received)")
            return 1, reply
        return 0, message.keyboard_locks()

    def _keyboard_press(self, hid_code: int) -> None:
        modifier_bit: int | None = KvmProtocol.modifier_bit(hid_code)
        if modifier_bit is not None:
            self._keyboard_modifier |= modifier_bit
            return
        if hid_code == 0 or hid_code in self._keyboard_keycodes:
            return
        for index in range(KvmProtocol.KEYCODE_SLOTS):
            if self._keyboard_keycodes[index] == 0:
                self._keyboard_keycodes[index] = hid_code
                return
        logger.warning("Keyboard buffer overflow (6KRO), key ignored")

    def _keyboard_release(self, hid_code: int) -> None:
        modifier_bit: int | None = KvmProtocol.modifier_bit(hid_code)
        if modifier_bit is not None:
            self._keyboard_modifier &= ~modifier_bit & 0xFF
            return
        for index in range(KvmProtocol.KEYCODE_SLOTS):
            if self._keyboard_keycodes[index] == hid_code:
                self._keyboard_keycodes[index] = 0

    def _send_keyboard_report(self) -> bool:
        return self._write(
            self._protocol.keyboard(
                self._keyboard_modifier, self._keyboard_keycodes
            )
        )

    ######################################################################
    # 鼠标（协议 §9 / §10）
    ######################################################################
    def mouse_send_event(self, command: str, buffer: MouseStateBuffer) -> None:
        if not self._ensure_control():
            return
        if command == "mouse_absolute_write":
            self.mouse_send_absolute_data(buffer)
        elif command == "mouse_relative_write":
            self.mouse_send_relative_data(buffer)
        else:
            logger.debug(f"Unhandled mouse command: {command}")

    def mouse_send_absolute_data(self, buffer: MouseStateBuffer) -> None:
        self._update_button_state(buffer)
        wheel: int = self._wheel_value(buffer)
        x_ratio, y_ratio = buffer.point.get()
        # 绝对模式下按键/滚轮在 Linux 上需要额外的相对事件，默认关闭
        if self.relative_click and not buffer.button.is_unknown():
            self._send_mouse_relative(0, 0, wheel)
            wheel = KvmProtocol.WHEEL_STOP
        self._send_mouse_absolute(
            KvmProtocol.normalize_absolute(x_ratio),
            KvmProtocol.normalize_absolute(y_ratio),
            wheel,
        )

    def mouse_send_relative_data(self, buffer: MouseStateBuffer) -> None:
        self._update_button_state(buffer)
        wheel: int = self._wheel_value(buffer)
        dx, dy = buffer.point.get()
        self._send_mouse_relative(dx, dy, wheel)

    def _update_button_state(self, buffer: MouseStateBuffer) -> int:
        """只在 PRESS/RELEASE 时改变按键位，UNKNOWN 表示"状态未变"。

        这样拖动时（坐标事件里的 button 恒为 UNKNOWN）不会把已按下的键
        误清掉——像 CH9329 驱动那样每次都发 "null" 会打断拖拽。
        """
        bit: int = self.MOUSE_BUTTON_BITS.get(buffer.button.code, 0)
        if bit == 0:
            return self._mouse_buttons
        if buffer.button.state == MouseButtonStateEnum.PRESS:
            self._mouse_buttons |= bit
        elif buffer.button.state == MouseButtonStateEnum.RELEASE:
            self._mouse_buttons &= ~bit & 0xFF
        return self._mouse_buttons

    @staticmethod
    def _wheel_value(buffer: MouseStateBuffer) -> int:
        """协议 §9：滚轮上滚为正"""
        if buffer.wheel == MouseWheelStateEnum.UP:
            return KvmProtocol.WHEEL_UP
        if buffer.wheel == MouseWheelStateEnum.DOWN:
            return KvmProtocol.WHEEL_DOWN
        return KvmProtocol.WHEEL_STOP

    def _send_mouse_relative(self, dx: float, dy: float, wheel: int) -> bool:
        return self._write(
            self._protocol.mouse_relative(
                self._mouse_buttons, int(dx), int(dy), wheel
            )
        )

    def _send_mouse_absolute(self, x: int, y: int, wheel: int) -> bool:
        self._last_absolute_point = (int(x), int(y))
        self._absolute_sent = True
        return self._write(
            self._protocol.mouse_absolute(self._mouse_buttons, x, y, wheel)
        )


if __name__ == "__main__":
    pass
