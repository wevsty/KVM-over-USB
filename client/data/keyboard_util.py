import platform

from .keyboard_text_to_hid_code import TEXT_TO_HID_CODE
from .keyboard_os_key_code_to_hid_code import (
    WINDOWS_SCANCODE_TO_HID_CODE,
    XCB_KEY_CODE_TO_HID_CODE,
    MACOS_VIRTUAL_KEY_CODE_TO_HID_CODE,
    QT_KEY_VALUE_TO_HID_CODE,
)

def qt_key_event_to_hid_code(event: QKeyEvent) -> tuple[bool, int]:
    status: bool = False
    key_code: int = 0x00
    hid_code: int | None = None
    system_name: str = platform.system()
    if system_name == "Windows":
        vk_code = event.nativeVirtualKey()
        if vk_code == 0xe7: # VK_PACKET
            hid_code = TEXT_TO_HID_CODE.get(event.text(), 0x00)
            status = True
        else:
            key_code = event.nativeScanCode()
            if key_code != 0:
                hid_code = WINDOWS_SCANCODE_TO_HID_CODE.get(key_code, None)
                status = True
    elif system_name == "Linux":
        key_code = event.nativeScanCode()
        if key_code != 0:
            hid_code = XCB_KEY_CODE_TO_HID_CODE.get(key_code, None)
            status = True
    elif system_name == "Darwin":
        # MacOS 下 nativeScanCode() 无法正常工作
        # 选择使用 nativeVirtualKey() 替代
        key_code = event.nativeVirtualKey()
        if key_code != 0:
            hid_code = MACOS_VIRTUAL_KEY_CODE_TO_HID_CODE.get(key_code, None)
            status = True
    else:
        pass
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


if __name__ == "__main__":
    pass
