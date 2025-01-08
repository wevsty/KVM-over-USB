import typing
from collections import UserDict


class StatusBaseException(RuntimeError):
    pass


class StatusValueTypeException(StatusBaseException):
    pass


class StatusBuffer(UserDict[str, typing.Any]):
    def set_value(self, key: str, value: typing.Any) -> None:
        self.data[key] = value

    def get_value(self, key: str) -> typing.Any:
        return self.data[key]

    def set_number(self, key: str, value: int | float) -> None:
        if isinstance(value, (int, float)):
            self.set_value(key, value)
        else:
            raise StatusValueTypeException("The value type should be a int or float")

    def get_number(self, key: str) -> int | float:
        value = self.get_value(key)
        if isinstance(value, (int, float)):
            return value
        else:
            raise StatusValueTypeException("The value type should be a int or float")

    def set_string(self, key: str, value: str) -> None:
        if isinstance(value, str):
            self.set_value(key, value)
        else:
            raise StatusValueTypeException("The value type should be a string")

    def get_string(self, key: str) -> str:
        value = self.get_value(key)
        if isinstance(value, str):
            return value
        else:
            raise StatusValueTypeException("The value type should be a string")

    def set_bool(self, key: str, value: bool) -> None:
        if isinstance(value, bool):
            self.set_value(key, value)
        else:
            raise StatusValueTypeException("The value type should be a bool")

    def get_bool(self, key: str) -> bool:
        value = self.get_value(key)
        if isinstance(value, bool):
            return value
        else:
            raise StatusValueTypeException("The value type should be a bool")

    # 反转bool
    def reverse_bool(self, key: str) -> None:
        value = self.get_value(key)
        if not isinstance(value, bool):
            raise StatusValueTypeException("The value type should be a bool")
        next_value = not value
        self.set_bool(key, next_value)

    def is_opened(self, key: str) -> bool:
        value = self.get_bool(key)
        return value

    def is_enabled(self, key: str) -> bool:
        value = self.get_bool(key)
        return value


if __name__ == "__main__":
    pass
