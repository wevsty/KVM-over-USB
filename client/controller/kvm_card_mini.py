import time
import typing

import hid
from loguru import logger

from controller.base import ControllerDeviceBase
from keyboard_buffer import KeyboardKeyBuffer, KeyStateEnum
from mouse_buffer import (
    MouseButtonCodeEnum,
    MouseButtonStateEnum,
    MouseStateBuffer,
    MouseWheelStateEnum,
)

VERBOSE_LOG_OUTPUT: bool = True


class KvmCardMiniHidBuffer:
    # HID Code 转换为 buffer[2] 的表
    HID_CODE_TO_B2_CODE: dict[int, int] = {
        # Left Control
        0xE0: 1,
        # Left Shift
        0xE1: 2,
        # Left Alt
        0xE2: 4,
        # Left GUI
        0xE3: 8,
        # Right Control
        0xE4: 16,
        # Right Shift
        0xE5: 32,
        # Right Alt
        0xE6: 64,
        # Right GUI
        0xE7: 128,
    }

    def __init__(self):
        self.keyboard_buffer: list[int] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.mouse_abs_buffer: list[int] = [2, 0, 0, 0, 0, 0, 0, 0, 0]
        self.mouse_rel_buffer: list[int] = [7, 0, 0, 0, 0, 0, 0, 0, 0]
        self.ws2812b_buffer: list[int] = [5, 0, 0, 0, 0, 0]

    def reset_buffer(self) -> None:
        self.keyboard_buffer: list[int] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.mouse_abs_buffer: list[int] = [2, 0, 0, 0, 0, 0, 0, 0, 0]
        self.mouse_rel_buffer: list[int] = [7, 0, 0, 0, 0, 0, 0, 0, 0]
        self.ws2812b_buffer: list[int] = [5, 0, 0, 0, 0, 0]

    def update_ws2812b(self, r: int, g: int, b: int) -> None:
        r = min(max(int(r), 0), 255)
        g = min(max(int(g), 0), 255)
        b = min(max(int(b), 0), 255)
        self.ws2812b_buffer[2] = r
        self.ws2812b_buffer[3] = g
        self.ws2812b_buffer[4] = b

    def keyboard_press(self, hid_code: int) -> bool:
        status: bool = False
        b2_code = self.HID_CODE_TO_B2_CODE.get(hid_code, 0)
        if b2_code != 0:
            self.keyboard_buffer[2] |= b2_code
            status = True
            return status
        for i in range(4, 10):
            if self.keyboard_buffer[i] == hid_code:
                # 说明此按键已经被按下
                status = True
                break
            if self.keyboard_buffer[i] == 0:
                self.keyboard_buffer[i] = hid_code
                status = True
                break
        if not status:
            logger.warning(
                "Buffer overflow: pressed too many keys at the same time."
            )
        return status

    def keyboard_release(self, hid_code: int) -> bool:
        status: bool = False
        b2_code = self.HID_CODE_TO_B2_CODE.get(hid_code, 0)
        if b2_code != 0:
            self.keyboard_buffer[2] &= ~b2_code
            status = True
            return status
        for i in range(4, 10):
            if self.keyboard_buffer[i] == hid_code:
                # 说明此按键已经被松开
                status = True
                self.keyboard_buffer[i] = 0
        return status

    def keyboard_reset(self) -> None:
        self.keyboard_buffer: list[int] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    @staticmethod
    def mouse_state_buffer_to_b2(buffer: MouseStateBuffer) -> int:
        button_code = buffer.button.code
        if button_code == MouseButtonCodeEnum.LEFT_BUTTON:
            return 1
        elif button_code == MouseButtonCodeEnum.RIGHT_BUTTON:
            return 2
        elif button_code == MouseButtonCodeEnum.MIDDLE_BUTTON:
            return 4
        elif button_code == MouseButtonCodeEnum.XBUTTON1_BUTTON:
            return 8
        elif button_code == MouseButtonCodeEnum.XBUTTON2_BUTTON:
            return 16
        else:
            return 0

    def update_mouse_absolute_buffer(self, buffer: MouseStateBuffer) -> None:
        hid_buffer = self.mouse_abs_buffer
        # 填充按键信息
        mouse_button_code = self.mouse_state_buffer_to_b2(buffer)
        mouse_button_state = buffer.button.state
        if mouse_button_state == MouseButtonStateEnum.PRESS:
            hid_buffer[2] = hid_buffer[2] | mouse_button_code
        elif mouse_button_state == MouseButtonStateEnum.RELEASE:
            hid_buffer[2] = hid_buffer[2] ^ mouse_button_code
            if hid_buffer[2] < 0 or hid_buffer[2] > 7:
                hid_buffer[2] = 0
        else:
            hid_buffer[2] = 0

        # 填充鼠标坐标
        x_hid = buffer.point.x
        y_hid = buffer.point.y
        x_hid = int(x_hid * 0x7FFF)
        y_hid = int(y_hid * 0x7FFF)
        hid_buffer[3] = x_hid & 0xFF
        hid_buffer[4] = x_hid >> 8
        hid_buffer[5] = y_hid & 0xFF
        hid_buffer[6] = y_hid >> 8

        # 填充滚轮信息
        wheel_bit = 7
        mouse_wheel_state = buffer.wheel
        if mouse_wheel_state == MouseWheelStateEnum.DOWN:
            hid_buffer[wheel_bit] = 0x01
        elif mouse_wheel_state == MouseWheelStateEnum.UP:
            hid_buffer[wheel_bit] = 0xFF
        else:
            hid_buffer[wheel_bit] = 0x00

    def update_mouse_relative_buffer(self, buffer: MouseStateBuffer) -> None:
        hid_buffer = self.mouse_rel_buffer
        # 填充按键信息
        mouse_button_code = self.mouse_state_buffer_to_b2(buffer)
        mouse_button_state = buffer.button.state
        if mouse_button_state == MouseButtonStateEnum.PRESS:
            hid_buffer = hid_buffer[2] | mouse_button_code
        elif mouse_button_state == MouseButtonStateEnum.RELEASE:
            hid_buffer[2] = hid_buffer[2] ^ mouse_button_code
            if hid_buffer[2] < 0 or hid_buffer[2] > 7:
                hid_buffer[2] = 0
        else:
            hid_buffer[2] = 0

        # 填充鼠标坐标
        x_hid = int(buffer.point.x)
        y_hid = int(buffer.point.y)
        hid_buffer[3] = x_hid & 0xFF
        hid_buffer[4] = y_hid & 0xFF

        # 填充滚轮信息
        wheel_bit = 5
        mouse_wheel_state = buffer.wheel
        if mouse_wheel_state == MouseWheelStateEnum.DOWN:
            hid_buffer[wheel_bit] = 0x01
        elif mouse_wheel_state == MouseWheelStateEnum.UP:
            hid_buffer[wheel_bit] = 0xFF
        else:
            hid_buffer[wheel_bit] = 0x00

    def mouse_reset(self):
        self.mouse_abs_buffer: list[int] = [2, 0, 0, 0, 0, 0, 0, 0, 0]
        self.mouse_rel_buffer: list[int] = [7, 0, 0, 0, 0, 0, 0, 0, 0]


class ControllerKvmCardMini(ControllerDeviceBase):
    FUNCTION_KEYS = [
        "ctrl_left",
        "ctrl_right",
        "shift_left",
        "shift_right",
        "alt_left",
        "alt_right",
        "win_left",
        "win_right",
        "win_app",
    ]

    def __init__(self):
        self.product_id: int = 0x2107
        self.vendor_id: int = 0x413D
        self.usage_page: int = 0xFF00
        self.hid_device = hid.device()
        self.hid_device_path: bytes | None = None
        self.timeout: float = 1.0
        self.hid_buffer: KvmCardMiniHidBuffer = KvmCardMiniHidBuffer()

    def device_init(self, config: dict[str, typing.Any]) -> None:
        hid_enumerate: typing.List[typing.Dict[str : typing.Any]] = (
            hid.enumerate()
        )
        for i in range(len(hid_enumerate)):
            hid_device_info: typing.Dict[str : typing.Any] = hid_enumerate[i]
            vid = hid_device_info["vendor_id"]
            pid = hid_device_info["product_id"]
            page = hid_device_info["usage_page"]
            if (
                vid == self.vendor_id
                and pid == self.product_id
                and page == self.usage_page
            ):
                self.hid_device_path: bytes = hid_device_info["path"]
                product_string = hid_device_info["product_string"]
                logger.info(f"Found target device: {self.hid_device_path}")
                logger.info(f"Product: {product_string}")

    def device_open(self) -> bool:
        status = False
        if self.hid_device_path is None:
            return status
        self.hid_device.open_path(self.hid_device_path)
        self.hid_device.set_nonblocking(True)
        status = True
        self.update_board_indicator_light(30, 30, 0)
        return status

    def device_close(self) -> None:
        self.update_board_indicator_light(0, 30, 30)
        self.controller_release()
        self.hid_device.close()

    def device_check_connection(self) -> bool:
        result: bool = False
        try:
            self.hid_device.read(1)
            result = True
        except IOError as error:
            logger.error(error)
            pass
        return result

    # 设备事件
    # 返回0为成功
    # 返回非0为失败
    def device_event(
        self, command: str, buffer: typing.Any
    ) -> tuple[str, int, typing.Any]:
        status_code: int = self.generate_status_code(True)
        reply: typing.Any = None

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
        self.controller_release(device_type)
        pass

    def device_reset(self) -> None:
        self.controller_reset()
        pass

    ######################################################################
    # kvm-card-mini 控制器命令函数
    ######################################################################
    # 写入 command 到 HID 设备
    def write_hid_data(self, buffer: list[int]) -> int:
        buffer = buffer[-1:] + buffer[:-1]
        buffer[0] = 0
        try:
            self.hid_device.write(buffer)
        except (OSError, ValueError):
            logger.error("Error writing data to device")
            return 1
        except NameError:
            logger.error("Uninitialized device")
            return 4
        return 0

    def read_hid_data(self) -> tuple[int, list[int]]:
        status_code: int = 0
        data: list[int] | None = list()
        time_start = time.perf_counter()
        while True:
            try:
                data = self.hid_device.read(64)
            except (OSError, ValueError):
                logger.error("Error reading data from device")
                status_code = 2
                return status_code, data
            if data is not None and len(data) != 0:
                if VERBOSE_LOG_OUTPUT:
                    logger.debug(f"hid > {data}")
                break
            if time.perf_counter() - time_start > 5:
                logger.error("Device response timeout")
                status_code = 3
                break
        return status_code, data

    # 获取键盘状态（指示灯状态）
    def keyboard_receive_status(self) -> tuple[int, dict[str, bool]]:
        status: bool = False
        reply_dict: dict = dict()
        if not self.device_check_connection():
            return status, reply_dict

        # [3,0] 是要求返回键盘状态数据
        status_code = self.write_hid_data([3, 0])
        if status_code != 0:
            return status, reply_dict
        status_code, hid_data = self.read_hid_data()
        if status_code != 0:
            return status, reply_dict
        if hid_data[0] != 3:
            return status, reply_dict

        status_bit = hid_data[2]
        if status_bit & (1 << 0) != 0:
            reply_dict["num_lock"] = True
        else:
            reply_dict["num_lock"] = False

        if status_bit & (1 << 1) != 0:
            reply_dict["caps_lock"] = True
        else:
            reply_dict["caps_lock"] = False

        if status_bit & (1 << 2) != 0:
            reply_dict["scroll_lock"] = True
        else:
            reply_dict["scroll_lock"] = False
        status = True

        logger.debug(f"receive keyboard indicator: {status}")
        if status:
            logger.debug(f"num_lock: {reply_dict["num_lock"]}")
            logger.debug(f"caps_lock: {reply_dict["caps_lock"]}")
            logger.debug(f"scroll_lock: {reply_dict["scroll_lock"]}")
        status_code = self.generate_status_code(status)
        return status_code, reply_dict

    def keyboard_send_event(self, buffer: KeyboardKeyBuffer):
        keys = buffer.buffer()
        if len(keys) > 1:
            pass
        for key in keys:
            if key.state == KeyStateEnum.PRESS:
                self.hid_buffer.keyboard_press(key.code)
            else:
                self.hid_buffer.keyboard_release(key.code)
        self.write_hid_data(self.hid_buffer.keyboard_buffer)

    def keyboard_recv_event(self, _command: str) -> tuple[int, dict]:
        status_code, reply = self.keyboard_receive_status()
        return status_code, reply

    def mouse_send_event(self, command: str, buffer: MouseStateBuffer):
        if command == "mouse_absolute_write":
            self.hid_buffer.update_mouse_absolute_buffer(buffer)
            self.write_hid_data(self.hid_buffer.mouse_abs_buffer)
        elif command == "mouse_relative_write":
            self.hid_buffer.update_mouse_relative_buffer(buffer)
            self.write_hid_data(self.hid_buffer.mouse_rel_buffer)
        else:
            pass
        # self.hid_buffer.mouse_reset()

    def controller_release(self, release_type: str = "all"):
        if not self.device_check_connection():
            return
        if release_type == "mouse":
            self.hid_buffer.mouse_reset()
            self.write_hid_data(self.hid_buffer.mouse_abs_buffer)
            self.write_hid_data(self.hid_buffer.mouse_rel_buffer)
        elif release_type == "keyboard":
            self.hid_buffer.keyboard_reset()
            self.write_hid_data(self.hid_buffer.keyboard_buffer)
        elif release_type == "all" or release_type == "any":
            self.hid_buffer.reset_buffer()
            self.write_hid_data(self.hid_buffer.mouse_abs_buffer)
            self.write_hid_data(self.hid_buffer.mouse_rel_buffer)
            self.write_hid_data(self.hid_buffer.keyboard_buffer)
        else:
            logger.debug(f"unknown release type: {release_type}")

    def controller_reset(self):
        if not self.device_check_connection():
            return
        status_code = self.write_hid_data([3, 0])
        if status_code != 0:
            logger.error("Reset MCU failed.")
        else:
            logger.error("Reset MCU succeed.")

    def update_board_indicator_light(self, r: int, g: int, b: int):
        if not self.device_check_connection():
            return
        self.hid_buffer.update_ws2812b(r, g, b)
        self.write_hid_data(self.hid_buffer.ws2812b_buffer)


if __name__ == "__main__":
    pass
