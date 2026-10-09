from __future__ import annotations
from loguru import logger
from PySide6.QtGui import QKeyEvent

from data.keyboard_key_name_to_hid_code import KEY_NAME_TO_HID_CODE
from data.keyboard_util import (
    qt_key_event_to_hid_code,
    os_scancode_code_to_hid_code,
)


class KeyboardCodeData:
    def __init__(self):
        # dict[key_name, hid_code]
        self.key_name_to_hid_code: dict[str, int] = dict()
        # 载入数据
        self.load_keyboard_code_data()

    # 载入键盘代码数据
    def load_keyboard_code_data(self):
        self.key_name_to_hid_code = KEY_NAME_TO_HID_CODE

    # 转换 scan code 到 hid code
    @staticmethod
    def convert_scan_code_to_hid_code(scancode: int) -> tuple[bool, int]:
        status, hid_code = os_scancode_code_to_hid_code(scancode)
        if not status:
            logger.warning(f"Unknown keyboard scancode: {scancode}")
        return status, hid_code

    # 转换 QKeyEvent 为 hid code
    @staticmethod
    def convert_qt_key_event_to_hid_code(event: QKeyEvent) -> tuple[bool, int]:
        status, hid_code = qt_key_event_to_hid_code(event)
        if not status:
            logger.warning(
                f"Unknown keyboard key: "
                f"nativeScanCode={event.nativeScanCode()}"
                f"nativeVirtualKey={event.nativeVirtualKey()}"
                f"KeyValue={event.key()}"
            )
        return status, hid_code

    # 转换 key name 到 hid code
    def convert_key_name_to_hid_code(self, key_name: str) -> tuple[bool, int]:
        status: bool = False
        hid_code: int | None = self.key_name_to_hid_code.get(key_name, None)
        if hid_code is None:
            logger.warning(f"Unknown key name: {key_name}")
            hid_code: int = 0
            return status, hid_code
        else:
            status = True
        return status, hid_code
