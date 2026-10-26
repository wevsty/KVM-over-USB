import platform

from PySide6.QtGui import QKeyEvent

from data.keyboard_key_name_to_hid_code import KEY_NAME_TO_HID_CODE
from data.keyboard_os_key_code_to_hid_code import (
    WINDOWS_SCANCODE_TO_HID_CODE,
    XCB_KEY_CODE_TO_HID_CODE,
    MACOS_VIRTUAL_KEY_CODE_TO_HID_CODE,
    QT_KEY_VALUE_TO_HID_CODE,
)


def qt_key_event_to_hid_code(event: QKeyEvent) -> tuple[bool, int]:
    status: bool = False
    hid_code: int | None = None
    system_name: str = platform.system()
    if system_name == "Windows":
        vk_code = event.nativeVirtualKey()
        key_code = event.nativeScanCode()
        # VK_PACKET 0xE7
        if vk_code == 0xE7:
            text_data = event.text()
            hid_code = KEY_NAME_TO_HID_CODE.get(text_data, None)
        else:
            hid_code = WINDOWS_SCANCODE_TO_HID_CODE.get(key_code, None)
    elif system_name == "Linux":
        key_code = event.nativeScanCode()
        hid_code = XCB_KEY_CODE_TO_HID_CODE.get(key_code, None)
    elif system_name == "Darwin":
        # MacOS 下 nativeScanCode() 无法正常工作
        # 选择使用 nativeVirtualKey() 替代
        key_code = event.nativeVirtualKey()
        hid_code = MACOS_VIRTUAL_KEY_CODE_TO_HID_CODE.get(key_code, None)
    else:
        pass
    if hid_code is not None:
        status = True
    else:
        hid_code: int = 0x00
    return status, hid_code


def qt_key_code_to_hid_code(key_code: int) -> tuple[bool, int]:
    status: bool = False
    hid_code: int | None = None
    system_name: str = platform.system()
    if system_name == "Windows":
        hid_code = WINDOWS_SCANCODE_TO_HID_CODE.get(key_code, None)
    elif system_name == "Linux":
        hid_code = XCB_KEY_CODE_TO_HID_CODE.get(key_code, None)
    elif system_name == "Darwin":
        # MacOS
        hid_code = MACOS_VIRTUAL_KEY_CODE_TO_HID_CODE.get(key_code, None)
    else:
        # 不支持的OS
        pass

    if hid_code is not None:
        status = True
    else:
        hid_code: int = 0x00
    return status, hid_code


def qt_key_value_to_hid_code(key_code: int) -> tuple[bool, int]:
    status: bool = False
    hid_code: int | None = QT_KEY_VALUE_TO_HID_CODE.get(key_code, None)
    if hid_code is not None:
        status = True
    else:
        hid_code: int = 0x00
    return status, hid_code


def os_scancode_code_to_hid_code(key_code: int) -> tuple[bool, int]:
    status: bool = False
    hid_code: int | None = None
    system_name: str = platform.system()
    if system_name == "Windows":
        hid_code = WINDOWS_SCANCODE_TO_HID_CODE.get(key_code, None)
    elif system_name == "Linux":
        hid_code = XCB_KEY_CODE_TO_HID_CODE.get(key_code, None)
    else:
        pass

    if hid_code is not None:
        status = True
    else:
        hid_code: int = 0x00
    return status, hid_code


def key_name_to_hid_code(key_name: str) -> tuple[bool, int]:
    status: bool = False
    hid_code = KEY_NAME_TO_HID_CODE.get(key_name, None)
    if hid_code is not None:
        status = True
    else:
        hid_code: int = 0x00
    return status, hid_code


if __name__ == "__main__":
    pass
