from typing import List
from typing import Tuple
from typing import Union

import serial.serialutil
import serial.tools.list_ports
from serial import Serial

from ch9329.config import get_serial_number


def main():
    comports = serial.tools.list_ports.comports()
    comports = [i for i in comports if i.vid == 6790 and i.pid == 29987]
    print(f"{len(comports)} ch9329 found.")
    data: List[Tuple[str, str, Union[str, None]]] = []
    for i in serial.tools.list_ports.comports():
        if i.vid == 6790 and i.pid == 29987:
            try:
                ser = Serial(i.device, 9600, timeout=0.05)
                print("Parsing serail number...")
                serial_number = get_serial_number(ser)
                ser.close()
            except (serial.serialutil.SerialException, UnicodeDecodeError):
                serial_number = "error"
            data.append((serial_number, i.device, i.location))
    for serial_number, device, location in sorted(data):
        print(
            f"serial_number={serial_number}, "
            f"device={device}, "
            f"location={location}"
        )


if __name__ == "__main__":
    main()
