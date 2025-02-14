from enum import Enum

from serial import Serial

from ch9329.exceptions import ProtocolError
from ch9329.utils import get_packet

HEAD = b"\x57\xab"  # Frame header
ADDR = b"\x00"  # Address

CMD_GET_PARA_CFG = b"\x08"
LEN_GET_PARA_CFG = b"\x00"
DATA_GET_PARA_CFG = b""

CMD_SET_PARA_CFG = b"\x09"
LEN_SET_PARA_CFG = b"\x32"

USB_STRING_ENABLE_FLAG = b"\x87"

CMD_GET_USB_STRING = b"\x0a"
LEN_GET_USB_STRING = b"\x01"


class USBStringDescriptor(Enum):
    MANUFACTURER = b"\x00"
    PRODUCT = b"\x01"
    SERIAL_NUMBER = b"\x02"


CMD_SET_USB_STRING = b"\x0b"


def set_device_descriptors(
    ser: Serial, descriptor_type: USBStringDescriptor, description: str
):
    if len(description) > 23:
        raise ValueError("length of description should not be more than 23")

    description_bytes = description.encode("utf-8")
    packet = get_packet(
        HEAD,
        ADDR,
        CMD_GET_USB_STRING,
        LEN_GET_USB_STRING,
        descriptor_type.value,
    )
    ser.write(packet)
    ser.readline()  # Read the response packet

    # Construct the packet for CMD_SET_USB_STRING
    descriptor_length = len(description_bytes)
    if descriptor_length == 0:
        descriptor_length = (
            1  # Ensure there's at least one byte for an empty string
        )

    modified_data = (
        bytes([descriptor_type.value[0]])
        + bytes([descriptor_length])
        + description_bytes
    )

    modified_packet = get_packet(
        HEAD,
        ADDR,
        CMD_SET_USB_STRING,
        bytes([len(modified_data)]),
        modified_data,
    )
    ser.write(modified_packet)
    return_packet = ser.readline()
    # this packet is expected in response when the VID and PID are
    # successfully set
    expected_packet = b"W\xab\x00\x8b\x01\x00\x8e"
    if return_packet != expected_packet:
        raise ProtocolError(
            f"expected: {expected_packet}, received: {return_packet}"
        )


def get_parameters(ser: Serial):
    # this packet is sent to ch9329 in response to which it sends the
    # current configuration
    packet = get_packet(
        HEAD, ADDR, CMD_GET_PARA_CFG, LEN_GET_PARA_CFG, DATA_GET_PARA_CFG
    )
    ser.write(packet)
    data = ser.readall()
    if not data:
        raise ProtocolError(f"expected a response, received nothing")
    return data


def get_usb_string(ser: Serial, descriptor: USBStringDescriptor):
    ser.readall()  # clear old packets
    packet = get_packet(
        HEAD,
        ADDR,
        CMD_GET_USB_STRING,
        LEN_GET_USB_STRING,
        descriptor.value,
    )
    ser.write(packet)
    data = ser.readall()
    if len(data) < 7:
        raise ProtocolError(
            f"expected a response of a least 7 bytes, received {len(data)} bytes"
        )
    length = data[6]
    return data[7 : 7 + length].decode()


def get_serial_number(ser: Serial):
    return get_usb_string(ser, USBStringDescriptor.SERIAL_NUMBER)


def get_manufacturer(ser: Serial):
    return get_usb_string(ser, USBStringDescriptor.MANUFACTURER)


def get_product(ser: Serial):
    return get_usb_string(ser, USBStringDescriptor.PRODUCT)


def set_device_ids(
    ser: Serial, vid: int, pid: int, custom_descriptor: bool = False
):
    # this packet is sent to ch9329 in response to which it sends the
    # current configuration
    packet = get_packet(
        HEAD, ADDR, CMD_GET_PARA_CFG, LEN_GET_PARA_CFG, DATA_GET_PARA_CFG
    )
    ser.write(packet)
    received_packet = ser.readline()  # read the current configuration
    vid_bytes = vid.to_bytes(
        2, "little"
    )  # Convert VID to little-endian 2-byte format
    pid_bytes = pid.to_bytes(
        2, "little"
    )  # Convert PID to little-endian 2-byte format
    modified_data = (
        received_packet[5:16] + vid_bytes + pid_bytes + received_packet[20:55]
    )  # Replace VID and PID bytes
    if custom_descriptor:
        modified_data = (
            modified_data[:35] + USB_STRING_ENABLE_FLAG + modified_data[36:]
        )
    modified_packet = get_packet(
        HEAD, ADDR, CMD_SET_PARA_CFG, LEN_SET_PARA_CFG, modified_data
    )
    # Send modified packet with the new VID and PID
    ser.write(modified_packet)
    return_packet = ser.readline()  # Read the response packet
    # this packet is expected in response when the VID and PID are
    # successfully set
    expected_packet = b"W\xab\x00\x89\x01\x00\x8c"
    if return_packet != expected_packet:
        raise ProtocolError(
            f"expected response {expected_packet}, received {return_packet}"
        )
