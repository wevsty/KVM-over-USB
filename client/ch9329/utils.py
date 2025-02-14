from __future__ import annotations


def get_packet(
    head: bytes, addr: bytes, cmd: bytes, length: bytes, data: bytes
):
    head_hex_list = list(head)
    head_hex_sum = sum(head_hex_list)
    data_hex_list = list(data)
    data_hex_sum = sum(data_hex_list)
    checksum = (
        sum(
            [
                head_hex_sum,
                int.from_bytes(addr, byteorder="big"),
                int.from_bytes(cmd, byteorder="big"),
                int.from_bytes(length, byteorder="big"),
                data_hex_sum,
            ]
        )
        % 256
    )
    packet = head + addr + cmd + length + data + bytes([checksum])
    return packet
