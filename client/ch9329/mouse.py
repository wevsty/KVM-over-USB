from __future__ import annotations

import random
import time
from typing import Literal

from serial import Serial

from ch9329.utils import get_packet

MouseCtrl = Literal["null", "left", "right", "center"]

ctrl_to_hex_mapping: dict[MouseCtrl, bytes] = {
    "null": b"\x00",
    "left": b"\x01",
    "right": b"\x02",
    "center": b"\x04",
}

HEAD = b"\x57\xab"  # Frame header
ADDR = b"\x00"  # Address
CMD_ABS = b"\x04"  # Command for absolute
CMD_REL = b"\x05"  # Command for relative
LEN_ABS = b"\x07"  # Data length for absolute
LEN_REL = b"\x05"  # Data length for relative


def wheel_int_to_bytes(wheel_delta: int):
    """
    Convert wheel_delta human readable integer to ch9329 readable bytes
    """
    # If the it is 0x00, it means there is no scrolling action
    # 0x01-0x7F, means scrolling upward
    # 0x81-0xFF, means scroll down
    if abs(wheel_delta) > 127:
        raise RuntimeError("Maximum wheel delta allowed is 127.")
    if wheel_delta >= 0:
        return (0x00 + wheel_delta).to_bytes(1)
    else:
        return (0x100 + wheel_delta).to_bytes(1)


def send_data_absolute(
    ser: Serial,
    x: int,
    y: int,
    ctrl: MouseCtrl = "null",
    x_max: int = 1920,
    y_max: int = 1080,
    wheel_delta: int = 0,
) -> None:
    # CMD_SEND_MS_ABS_DATA has exactly 7 bytes

    # first byte is alwasys 0x02
    data = b"\x02"

    # second byte is mouse button value
    data += ctrl_to_hex_mapping[ctrl]

    # third and fourth bytes are x-coordinates
    x_cur = (4096 * x) // x_max
    data += x_cur.to_bytes(2, byteorder="little")

    # fifth and sixth bytes are y-coordinates
    y_cur = (4096 * y) // y_max
    data += y_cur.to_bytes(2, byteorder="little")

    # seventh byte contains wheel data
    data += wheel_int_to_bytes(wheel_delta)

    packet = get_packet(HEAD, ADDR, CMD_ABS, LEN_ABS, data)
    ser.write(packet)


def send_data_relative(
    ser: Serial, x: int, y: int, ctrl: MouseCtrl = "null", wheel_delta: int = 0
) -> None:
    # first byte is alwasys 0x01
    data = b"\x01"

    # second byte is mouse button value
    data += ctrl_to_hex_mapping[ctrl]

    # third byte is x distance
    if x < 0:
        data += (0 - abs(x)).to_bytes(1, byteorder="big", signed=True)
    else:
        data += x.to_bytes(1, byteorder="big", signed=True)

    # forth byte is y distance
    if y < 0:
        data += (0 - abs(y)).to_bytes(1, byteorder="big", signed=True)
    else:
        data += y.to_bytes(1, byteorder="big", signed=True)

    # fifth byte contains wheel data
    data += wheel_int_to_bytes(wheel_delta)

    packet = get_packet(HEAD, ADDR, CMD_REL, LEN_REL, data)
    ser.write(packet)


def move(
    ser: Serial,
    x: int,
    y: int,
    relative: bool = False,
    monitor_width: int = 1920,
    monitor_height: int = 1080,
) -> None:
    if relative:
        send_data_relative(ser, x, y, "null")
    else:
        send_data_absolute(ser, x, y, "null", monitor_width, monitor_height)


def press(ser: Serial, button: MouseCtrl = "left") -> None:
    send_data_relative(ser, 0, 0, button)


def release(ser: Serial) -> None:
    send_data_relative(ser, 0, 0, "null")


def click(ser: Serial, button: MouseCtrl = "left") -> None:
    press(ser, button)
    # 100 to 450 milliseconds delay for simulating natural behavior
    time.sleep(random.uniform(0.1, 0.45))
    release(ser)


def wheel(ser: Serial, wheel: int = 1) -> None:
    send_data_relative(ser, 0, 0, wheel_delta=wheel)
