import os
from abc import ABC, abstractmethod

from loguru import logger

from controller_ch9329 import Controller
from keyboard_buffer import KeyboardStateBuffer, KeyStateEnum
from mouse_buffer import MouseStateBuffer, MouseWheelStateEnum, MouseButtonCodeEnum, \
    MouseButtonStateEnum

if os.name == "nt":  # sys.platform == "win32":
    from serial.tools.list_ports_windows import comports as list_comports
elif os.name == "posix":
    from serial.tools.list_ports_posix import comports as list_comports
else:
    raise ImportError("Sorry: no implementation for your platform {} available".format(os.name))


class ControllerDebugOptions:
    DEVICE: bool = False
    MOUSE: bool = False
    KEYBOARD: bool = False


GLOBAL_CONTROLLER_DEVICE: None = None


class ControllerDeviceBase(ABC):
    @abstractmethod
    def device_open(self) -> bool:
        pass

    @abstractmethod
    def device_close(self) -> None:
        pass

    @abstractmethod
    def device_check(self) -> bool:
        pass

    @abstractmethod
    def device_event(self, command: str, buffer: dict) -> tuple[int, dict]:
        pass


class ControllerDevice(ControllerDeviceBase):
    FUNCTION_KEYS = [
        "ctrl_left", "ctrl_right",
        "shift_left", "shift_right",
        "alt_left", "alt_right",
        "win_left", "win_right", "win_app"
    ]

    def __init__(self):
        self.port: str = "auto"
        self.baud: int = 9600
        self.screen_x: int = 1920
        self.screen_y: int = 1080
        self.controller: Controller = Controller()

    @staticmethod
    def detect_serial_ports() -> list[str]:
        port_name_list: list[str] = []
        port_info_list: serial.tools.list_ports.ListPortInfo = list_comports(include_links=False)
        for port_info in port_info_list:
            port_name_list.append(port_info.name)
        port_info_list.sort()
        return port_name_list

    def device_init(self, port: str, baud: int, screen_x: int, screen_y: int) -> None:
        self.port = port
        self.baud = baud
        self.screen_x = screen_x
        self.screen_y = screen_y

    def device_open(self) -> bool:
        status: bool = False
        if self.port == "auto":
            # 检测com端口
            ports: list[str] = self.detect_serial_ports()
            if len(ports) > 0:
                # 获取最后一个com端口
                self.port = ports[-1]
            else:
                self.port = ""
        if self.port == "":
            return status
        self.controller.set_connection_params(self.port, self.baud, self.screen_x, self.screen_y)
        if ControllerDebugOptions.DEVICE:
            logger.debug(
                f"create_connection({self.port}, {self.baud}, " +
                f"{self.screen_x}, {self.screen_y})"
            )
        status = self.controller.create_connection()
        if ControllerDebugOptions.DEVICE:
            if status:
                logger.debug(f"create_connection -> succeed")
                info = self.controller.product_info()
                logger.debug(f"product info: {info}")
            else:
                logger.debug(f"create_connection -> failed")
        return status

    def device_close(self) -> None:
        self.controller.release("all")
        self.controller.close_connection()

    def device_check(self) -> bool:
        return self.controller.check_connection()

    def device_release(self, device_type: str) -> None:
        known_type = ["mouse", "keyboard", "all", "any"]
        if device_type in known_type:
            self.controller.release(device_type)
        else:
            raise ValueError(f"unknown release type: {device_type}")

    def device_reset(self) -> None:
        self.controller.release("all")
        self.controller.reset_controller()

    # 设备事件
    # 返回0为成功
    # 返回非0为失败
    def device_event(self, command: str, buffer: object) -> tuple[str, int, object]:
        status_code: int = 0
        reply: object = None

        if command == "keyboard_write":
            self.keyboard_send_event(buffer)
        elif command == "keyboard_read":
            status_code, reply = self.keyboard_recv_event(command)
        elif command == "mouse_absolute_write":
            self.mouse_send_event(command, buffer)
        elif command == "mouse_relative_write":
            self.mouse_send_event(command, buffer)
        elif command == "device_open":
            status = self.device_open()
            if status is False:
                status_code = 1
        elif command == "device_close":
            self.device_close()
        elif command == "device_check":
            status = self.device_check()
            if status is False:
                status_code = 1
        elif command == "device_release":
            self.device_release(buffer)
        elif command == "device_reset":
            self.device_reset()
        else:
            logger.debug(f"Unhandled command: {command}")
            pass
        return command, status_code, reply

    def keyboard_recv_event(self, _command: str) -> tuple[int, dict]:
        status, reply = self.controller.keyboard_receive_status()
        if status is True:
            status_code = 0
        else:
            status_code = 1
        return status_code, reply

    def keyboard_send_event(self, buffer: KeyboardStateBuffer):
        keys = buffer.buffer()
        press_keys = list()
        press_function_keys = list()
        for key in keys:
            if key.state == KeyStateEnum.PRESS:
                key_name = self.controller.convert_hid_key_code_to_ch9329_key(key.code)
                if key_name in self.FUNCTION_KEYS:
                    press_function_keys.append(key_name)
                else:
                    press_keys.append(key_name)
        self.controller.keyboard_send_data(press_keys, press_function_keys)
        if ControllerDebugOptions.KEYBOARD:
            print_keys = press_keys + press_function_keys
            logger.debug(f"keyboard send: {print_keys}")

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
            self.controller.mouse_send_data("null", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.LEFT_BUTTON:
            self.controller.mouse_send_data("left", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.RIGHT_BUTTON:
            self.controller.mouse_send_data("right", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.MIDDLE_BUTTON:
            self.controller.mouse_send_data("center", real_x, real_y, wheel, False)
        elif buffer.button.code == MouseButtonCodeEnum.UNKNOWN_BUTTON:
            self.controller.mouse_send_data("null", x, y, wheel, True)
        else:
            if ControllerDebugOptions.MOUSE:
                logger.debug(f"unknown mouse button {buffer.button.code}")

    def mouse_send_relative_data(self, buffer: MouseStateBuffer):
        x, y = buffer.point.get()

        if x > 127:
            x = 127
        elif x < -128:
            x = -128
        else:
            pass

        if y > 127:
            y = 127
        elif y < -128:
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
            self.controller.mouse_send_data("null", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.LEFT_BUTTON:
            self.controller.mouse_send_data("left", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.RIGHT_BUTTON:
            self.controller.mouse_send_data("right", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.MIDDLE_BUTTON:
            self.controller.mouse_send_data("center", x, y, wheel, True)
        elif buffer.button.code == MouseButtonCodeEnum.UNKNOWN_BUTTON:
            self.controller.mouse_send_data("null", x, y, wheel, True)
        else:
            if ControllerDebugOptions.MOUSE:
                logger.debug(f"unknown mouse button {buffer.button.code}")


if __name__ == "__main__":
    pass
