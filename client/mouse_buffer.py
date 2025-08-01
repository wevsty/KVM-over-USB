from copy import deepcopy
from dataclasses import dataclass, field
from enum import IntEnum, auto


class MouseButtonStateEnum(IntEnum):
    PRESS = auto()
    RELEASE = auto()


class MouseButtonCodeEnum(IntEnum):
    LEFT_BUTTON = auto()
    RIGHT_BUTTON = auto()
    MIDDLE_BUTTON = auto()
    # BackButton
    XBUTTON1_BUTTON = auto()
    # ForwardButton
    XBUTTON2_BUTTON = auto()
    UNKNOWN_BUTTON = auto()


class MouseWheelStateEnum(IntEnum):
    UP = auto()
    DOWN = auto()
    STOP = auto()


@dataclass
class MouseButton:
    # 鼠标按键编码
    code: MouseButtonCodeEnum = MouseButtonCodeEnum.UNKNOWN_BUTTON
    # 按键对应状态编码
    state: MouseButtonStateEnum = MouseButtonStateEnum.RELEASE

    def get(self) -> tuple[MouseButtonCodeEnum, MouseButtonStateEnum]:
        return self.code, self.state

    def set(
        self, code: MouseButtonCodeEnum, state: MouseButtonStateEnum
    ) -> None:
        self.code = code
        self.state = state

    def reset(self):
        self.code = MouseButtonCodeEnum.UNKNOWN_BUTTON
        self.state = MouseButtonStateEnum.RELEASE


@dataclass
class MousePoint:
    x: float = 0
    y: float = 0

    def get(self) -> tuple[float, float]:
        return self.x, self.y

    def set(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def reset(self) -> None:
        self.set(0, 0)


@dataclass
class MouseStateBuffer:
    point: MousePoint = field(default_factory=MousePoint)
    button: MouseButton = field(default_factory=MouseButton)
    wheel: MouseWheelStateEnum = MouseWheelStateEnum.STOP

    def get_point(self) -> tuple[float, float]:
        return self.point.get()

    def set_point(self, x: float, y: float) -> None:
        self.point.set(x, y)

    def set_button(
        self, code: MouseButtonCodeEnum, state: MouseButtonStateEnum
    ) -> None:
        self.button.set(code, state)

    def get_button(self) -> tuple[MouseButtonCodeEnum, MouseButtonStateEnum]:
        return self.button.get()

    def set_wheel(self, state: MouseWheelStateEnum):
        self.wheel = state

    def get_wheel(self) -> MouseWheelStateEnum:
        return self.wheel

    def clear_point(self) -> None:
        self.point.reset()

    def clear_button(self) -> None:
        self.button.reset()

    def clear_wheel(self) -> None:
        self.wheel = MouseWheelStateEnum.STOP

    def clear(self) -> None:
        self.clear_point()
        self.clear_button()
        self.clear_wheel()

    def dup(self):
        copy = MouseStateBuffer()
        copy.point = deepcopy(self.point)
        copy.button = deepcopy(self.button)
        copy.wheel = self.wheel
        return copy


if __name__ == "__main__":
    pass
