from copy import deepcopy
from dataclasses import dataclass
from enum import IntEnum, auto


class KeyStateEnum(IntEnum):
    PRESS = auto()
    RELEASE = auto()


@dataclass
class KeyStateItem:
    code: int
    state: KeyStateEnum

    def __str__(self):
        return f"KeyStateItem(code={self.code}, state={self.state.name})"


class KeyboardKeyBuffer:
    def __init__(self):
        self.keyboard_buffer: list[KeyStateItem] = list()

    def key_press(self, key_code: int):
        exist_flag = False
        for ks in self.keyboard_buffer:
            if ks.code == key_code:
                exist_flag = True
        if not exist_flag:
            self.keyboard_buffer.append(
                KeyStateItem(key_code, KeyStateEnum.PRESS)
            )

    def key_release(self, key_code: int):
        for ks in self.keyboard_buffer:
            if ks.code == key_code:
                ks.state = KeyStateEnum.RELEASE

    def key_state(self, key_code: int):
        for ks in self.keyboard_buffer:
            if ks.code == key_code:
                return ks.state
        return KeyStateEnum.RELEASE

    def is_pressed(self, key_code: int):
        pressed: bool = False
        for ks in self.keyboard_buffer:
            if ks.code == key_code and ks.state == KeyStateEnum.PRESS:
                pressed = True
        return pressed

    def clear_released(self):
        replace_buffer: list[KeyStateItem] = list()
        for ks in self.keyboard_buffer:
            if ks.state == KeyStateEnum.RELEASE:
                continue
            replace_buffer.append(ks)
        self.keyboard_buffer = replace_buffer

    def clear(self):
        self.keyboard_buffer.clear()

    def buffer(self) -> list[KeyStateItem]:
        return self.keyboard_buffer

    def dup(self):
        copy_self = KeyboardKeyBuffer()
        copy_self.keyboard_buffer = deepcopy(self.keyboard_buffer)
        return copy_self

    def __str__(self):
        item_string = ", ".join(str(item) for item in self.keyboard_buffer)
        return_string = "[%s]" % item_string
        return return_string


class KeyboardIndicatorBuffer:
    def __init__(self):
        self.caps_lock: bool = False
        self.scroll_lock: bool = False
        self.num_lock: bool = False

    def clear(self):
        self.caps_lock = False
        self.scroll_lock = False
        self.num_lock = False

    def from_dict(self, data: dict[str, bool]):
        self.caps_lock = data.get("caps_lock", False)
        self.scroll_lock = data.get("scroll_lock", False)
        self.num_lock = data.get("num_lock", False)

    def to_dict(self) -> dict[str, bool]:
        reply_dict = {
            "num_lock": self.num_lock,
            "caps_lock": self.caps_lock,
            "scroll_lock": self.scroll_lock,
        }
        return reply_dict

    def __str__(self):
        return str(self.to_dict())


if __name__ == "__main__":
    pass
