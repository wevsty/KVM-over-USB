class HexConvert:
    @staticmethod
    def hex_to_int(data: str) -> int:
        return int(data, 16)

    @staticmethod
    def int_to_hex(data: int, fmt: str = "0x{:02x}") -> str:
        return fmt.format(data)


if __name__ == "__main__":
    pass
