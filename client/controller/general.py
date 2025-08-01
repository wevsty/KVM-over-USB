import threading
import typing

from controller.base import ControllerDeviceBase
from controller.ch9329 import ControllerCh9329
from controller.kvm_card_mini import ControllerKvmCardMini


class ControllerGeneralDevice(ControllerDeviceBase):
    def __init__(self):
        self.controller_dict: dict[str, type[ControllerDeviceBase]] = {
            "ch9329": ControllerCh9329,
            "kvm-card-mini": ControllerKvmCardMini,
        }
        self.controller_type: str = ""
        self.controller: ControllerDeviceBase | None = None
        self.config: dict[str, typing.Any] = dict()
        self.mutex: threading.Lock = threading.Lock()
        pass

    def device_init(self, buffer: typing.Any) -> bool:
        with self.mutex:
            self.config: dict[str, typing.Any] = buffer
            self.controller_type = self.config["controller_type"]
            self.controller = self.controller_dict[self.controller_type]()
            # 剩余参数传递给控制器实现
            status = self.controller.device_init(buffer)
        return status

    def device_open(self) -> bool:
        return self.controller.device_open()

    def device_close(self) -> None:
        return self.controller.device_close()

    def device_check_connection(self) -> bool:
        return self.controller.device_check_connection()

    # 设备事件
    # 返回0为成功
    # 返回非0为失败
    def device_event(
        self, command: str, buffer: typing.Any
    ) -> tuple[str, int, typing.Any]:
        status_code: int = self.generate_status_code(True)
        reply: typing.Any = None

        if command == "device_open":
            status = self.device_open()
            status_code = self.generate_status_code(status)
        elif command == "device_close":
            self.device_close()
        elif command == "device_check_connection":
            status = self.device_check_connection()
            status_code = self.generate_status_code(status)
        else:
            command, status_code, reply = self.controller.device_event(
                command, buffer
            )
        return command, status_code, reply


if __name__ == "__main__":
    pass
