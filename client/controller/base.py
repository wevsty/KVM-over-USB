import typing
from abc import ABC, abstractmethod


class ControllerDeviceBase(ABC):
    @staticmethod
    def generate_status_code(value: bool) -> int:
        if value:
            status_code = 0
        else:
            status_code = 1
        return status_code

    @abstractmethod
    def device_init(self, buffer: typing.Any) -> bool:
        pass

    @abstractmethod
    def device_open(self) -> bool:
        pass

    @abstractmethod
    def device_close(self) -> None:
        pass

    @abstractmethod
    def device_check_connection(self) -> bool:
        pass

    @abstractmethod
    def device_event(
        self, command: str, buffer: typing.Any
    ) -> tuple[str, int, typing.Any]:
        pass


if __name__ == "__main__":
    pass
