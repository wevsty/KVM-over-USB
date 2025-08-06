import typing

from loguru import logger
from pych9329 import chip_command, keyboard, mouse
from serial import Serial
import random
from controller.base import ControllerDeviceBase
from controller.serial_device import SerialDevice
from data.keyboard_hid_code_to_key_name import HID_CODE_TO_KEY_NAME
from keyboard_buffer import KeyboardKeyBuffer, KeyStateEnum
from mouse_buffer import (
    MouseButtonCodeEnum,
    MouseButtonStateEnum,
    MouseStateBuffer,
    MouseWheelStateEnum,
)


class ControllerCh9329(ControllerDeviceBase):
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
        self.hid_code_to_key_name: dict[int, str] = HID_CODE_TO_KEY_NAME
        self.connection: Serial | None = None
        self.port: str = "auto"
        self.baud_rate: int = 9600
        self.timeout: float = 1.0
        self.screen_x: int = 0
        self.screen_y: int = 0

        self.min_interval: float = 0.2
        self.max_interval: float = 0.5

    def random_interval(self) -> float:
        return random.uniform(self.min_interval, self.max_interval)

    def device_init(self, config: dict[str, typing.Any]) -> None:
        self.port: str = config["port"]
        self.baud_rate: int = config["baud_rate"]
        self.timeout: int = config["timeout"]
        self.screen_x: int = config["resolution_x"]
        self.screen_y: int = config["resolution_y"]

    def device_open(self) -> bool:
        status, self.connection = SerialDevice.create_serial_connection(
            self.port, self.baud_rate, self.timeout
        )
        if not status:
            self.connection = None
        return status

    def device_close(self) -> None:
        self.ch9329_release("all")
        SerialDevice.close_serial_connection(self.connection)
        self.connection = None

    def check_connection(self) -> bool:
        result: bool = False
        if self.connection is None:
            return result
        result = self.connection.is_open
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
            self.ch9329_release(buffer)
        elif command == "device_reset":
            self.device_reset()
        else:
            logger.debug(f"Unhandled command: {command}")

        return command, status_code, reply

    def device_release(self, device_type: str) -> None:
        known_type = ["mouse", "keyboard", "all", "any"]
        if device_type in known_type:
            self.ch9329_release(device_type)
        else:
            raise ValueError(f"unknown release type: {device_type}")

    def device_reset(self) -> None:
        self.ch9329_release("all")
        self.ch9329_reset()

    def keyboard_recv_event(self, _command: str) -> tuple[int, dict]:
        status_code, reply = self.keyboard_receive_status()
        return status_code, reply

    def keyboard_send_event(self, buffer: KeyboardKeyBuffer):
        keys = buffer.buffer()
        press_keys = list()
        press_function_keys = list()
        for key in keys:
            if key.state == KeyStateEnum.PRESS:
                key_name = self.convert_hid_code_to_key_name(key.code)
                if key_name in self.FUNCTION_KEYS:
                    press_function_keys.append(key_name)
                else:
                    press_keys.append(key_name)
        self.keyboard_send_data(press_keys, press_function_keys)

    def mouse_send_event(self, command: str, buffer: MouseStateBuffer):
        if command == "mouse_absolute_write":
            self.mouse_send_absolute_data(buffer)
        elif command == "mouse_relative_write":
            self.mouse_send_relative_data(buffer)
        else:
            pass

    def mouse_send_absolute_data(self, buffer: MouseStateBuffer):
        x, y = buffer.point.get()
        real_x = int(round(x * self.screen_x))
        real_y = int(round(y * self.screen_y))

        # 确保值不会超过屏幕范围
        real_x = min(real_x, self.screen_x)
        real_y = min(real_y, self.screen_y)

        if buffer.wheel == MouseWheelStateEnum.UP:
            # 滚轮向上
            wheel = -1
        elif buffer.wheel == MouseWheelStateEnum.DOWN:
            # 滚轮向下
            wheel = 1
        else:
            # 滚轮不动
            wheel = 0

        if buffer.button.state == MouseButtonStateEnum.RELEASE:
            self.mouse_send_data("null", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.LEFT_BUTTON:
            self.mouse_send_data("left", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.RIGHT_BUTTON:
            self.mouse_send_data("right", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.MIDDLE_BUTTON:
            self.mouse_send_data("center", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.UNKNOWN_BUTTON:
            self.mouse_send_data("null", 0, 0, wheel, True)
        else:
            logger.debug(f"unknown mouse button {buffer.button.code}")

    def mouse_send_relative_data(self, buffer: MouseStateBuffer):
        x, y = buffer.point.get()
        x = int(x)
        y = int(y)

        if x >= 127:
            x = 127
        elif x <= -128:
            x = -128
        else:
            pass

        if y >= 127:
            y = 127
        elif y <= -128:
            y = -128
        else:
            pass

        assert -128 <= x <= 127
        assert -128 <= y <= 127

        if buffer.wheel == MouseWheelStateEnum.UP:
            # 滚轮向上
            wheel = -1
        elif buffer.wheel == MouseWheelStateEnum.DOWN:
            # 滚轮向下
            wheel = 1
        else:
            # 滚轮不动
            wheel = 0

        if buffer.button.state == MouseButtonStateEnum.RELEASE:
            self.mouse_send_data("null", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.LEFT_BUTTON:
            self.mouse_send_data("left", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.RIGHT_BUTTON:
            self.mouse_send_data("right", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.MIDDLE_BUTTON:
            self.mouse_send_data("center", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.UNKNOWN_BUTTON:
            self.mouse_send_data("null", x, y, wheel, True)
        else:
            logger.debug(f"unknown mouse button {buffer.button.code}")

    ######################################################################
    # ch9329控制器命令函数
    ######################################################################
    # hid code 转换成 键名称
    def convert_hid_code_to_key_name(self, code: int) -> str:
        key_name: str | None = self.hid_code_to_key_name.get(code, None)
        if key_name is None:
            logger.error(f"Key name not found: {key_name}")
            key_name = ""
        return key_name

    def mouse_send_data(
        self,
        button_name: str,
        x: int = 0,
        y: int = 0,
        wheel: int = 0,
        relative: bool = False,
    ):
        if not self.check_connection():
            return
        if not relative:
            mouse.send_absolute_data(
                self.connection,
                x,
                y,
                button_name,
                self.screen_x,
                self.screen_y,
                wheel,
            )
        else:
            mouse.send_relative_data(self.connection, x, y, button_name, wheel)

    def keyboard_send_data(self, keys: list, function_keys: list):
        if not self.check_connection():
            return False
        if len(keys) > 6:
            keys = keys[0:6]
        if len(function_keys) > 8:
            function_keys = function_keys[0:8]
        keyboard.trigger(self.connection, keys, function_keys)
        # logger.debug(f"keyboard keys trigger : {keys}")
        return True

    # 获取键盘状态（指示灯状态）
    def keyboard_receive_status(self) -> tuple[int, dict[str, bool]]:
        status: bool = False
        reply_dict: dict = dict()
        if not self.check_connection():
            return status, reply_dict
        # clear connection buffer
        # self.connection.readall()
        status, reply_dict = keyboard.receive_indicator_status(self.connection)

        logger.debug(f"receive keyboard indicator: {status}")
        if status:
            logger.debug(
                f"keyboard usb connect: {reply_dict["usb_connect_status"]}"
            )
            logger.debug(f"num_lock: {reply_dict["num_lock"]}")
            logger.debug(f"caps_lock: {reply_dict["caps_lock"]}")
            logger.debug(f"scroll_lock: {reply_dict["scroll_lock"]}")
        status_code = self.generate_status_code(status)
        return status_code, reply_dict

    def ch9329_release(self, release_type: str = "all"):
        if not self.check_connection():
            return
        if release_type == "mouse":
            mouse.release(self.connection)
        elif release_type == "keyboard":
            keyboard.release(self.connection)
        elif release_type == "all" or release_type == "any":
            mouse.release(self.connection)
            keyboard.release(self.connection)
        else:
            logger.debug(f"unknown release type: {release_type}")

    # 复位芯片
    def ch9329_reset(self):
        if not self.check_connection():
            return
        chip_command.send_command_reset(self.connection)
        self.connection.flush()
        self.device_close()

    # 恢复出厂设置
    def ch9329_restore_factory_settings(self):
        if not self.check_connection():
            return
        chip_command.send_command_restore_factory_config(self.connection)


if __name__ == "__main__":
    pass
