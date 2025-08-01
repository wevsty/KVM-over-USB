import os

from loguru import logger
from serial import Serial, SerialException

# sys.platform == "win32"
if os.name == "nt":
    from serial.tools.list_ports_common import ListPortInfo
    from serial.tools.list_ports_windows import comports as list_comports
elif os.name == "posix":
    from serial.tools.list_ports_common import ListPortInfo
    from serial.tools.list_ports_posix import comports as list_comports
else:
    raise ImportError(
        "Sorry: no implementation for your platform {} available".format(
            os.name
        )
    )


class SerialDevice:
    # 列出串口
    @staticmethod
    def list_serial_ports() -> list[str]:
        port_name_list: list[str] = []
        port_info_list: list[ListPortInfo] = list_comports(include_links=False)
        for port_info in port_info_list:
            port_name_list.append(port_info.name)
        port_info_list.sort()
        return port_name_list

    # 建立串行连接
    @staticmethod
    def create_serial_connection(
        port_name: str, baud_rate: int, timeout: float = 1
    ) -> tuple[bool, Serial | None]:
        result: bool = False
        connection: Serial | None = None
        # 处理端口号为auto的情况
        if port_name == "auto":
            ports: list[str] = SerialDevice.list_serial_ports()
            if len(ports) > 0:
                # 获取最后一个com端口
                port_name = ports[-1]
            else:
                port_name = ""
        if port_name == "":
            logger.info("Port name cannot be empty.")
            return result, connection
        try:
            connection = Serial(port_name, baud_rate, timeout=timeout)
            result = True
        except SerialException as err:
            connection = None
            result = False
            logger.error(err)
        return result, connection

    # 关闭串行连接
    @staticmethod
    def close_serial_connection(serial: Serial | None) -> None:
        if serial is not None:
            serial.close()


if __name__ == "__main__":
    pass
