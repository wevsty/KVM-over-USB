from __future__ import annotations

import typing
from collections import UserDict


class StatusBaseException(RuntimeError):
    pass


class StatusKeyError(StatusBaseException):
    pass


class StatusValueError(StatusBaseException):
    pass


class StatusBuffer(UserDict[str, typing.Any]):
    """进程内共享状态缓冲（UserDict 语义保持不变）。

    状态本身同步持有/读取，事件处理路径要求低延迟，故不改为异步查询。
    为支持『状态变更通知』，提供轻量观察者机制：add_change_listener 注册
    回调，任意写入（set_* / create / delete / reverse_bool 等内置写入方法）
    后同步调用回调 (key, value)。本类不依赖任何 Qt / 总线实现，保持通用、
    无全局 Qt 引入；Qt 侧的信号转发由 AppEventBus 在构造时订阅本观察者负责。
    """

    def __init__(
        self, initial_data: typing.Mapping[str, typing.Any] | None = None
    ):
        super().__init__(initial_data)
        self._change_listeners: list[
            typing.Callable[[str, typing.Any], None]
        ] = []

    def add_change_listener(
        self, listener: typing.Callable[[str, typing.Any], None]
    ) -> None:
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)

    def remove_change_listener(
        self, listener: typing.Callable[[str, typing.Any], None]
    ) -> None:
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)

    def _notify_change(self, key: str, value: typing.Any) -> None:
        for listener in self._change_listeners:
            listener(key, value)

    def exists(self, key: str) -> bool:
        if key in self.data:
            return True
        return False

    def create(self, key: str, value: typing.Any = None) -> None:
        self.data[key] = value
        self._notify_change(key, value)

    def delete(self, key: str) -> None:
        self.data.pop(key, None)
        # 删除也通知（值为 None），订阅方可据此清理
        self._notify_change(key, None)

    def value(self, key: str) -> typing.Any:
        return self.data[key]

    def set_value(self, key: str, value: typing.Any) -> None:
        self.data[key] = value
        self._notify_change(key, value)

    def get_value(self, key: str) -> typing.Any:
        return self.data[key]

    def set_number(self, key: str, value: int | float) -> None:
        self.set_value(key, value)

    def get_number(self, key: str) -> int | float:
        value = self.get_value(key)
        if isinstance(value, (int, float)):
            return value
        else:
            raise StatusValueError("The value type should be a int or float")

    def set_string(self, key: str, value: str) -> None:
        self.set_value(key, value)

    def get_string(self, key: str) -> str:
        value = self.get_value(key)
        if isinstance(value, str):
            return value
        else:
            raise StatusValueError("The value type should be a string")

    def set_bool(self, key: str, value: bool) -> None:
        self.set_value(key, value)

    def get_bool(self, key: str) -> bool:
        value = self.get_value(key)
        if isinstance(value, bool):
            return value
        else:
            raise StatusValueError("The value type should be a bool")

    # 反转bool
    def reverse_bool(self, key: str) -> None:
        value = self.get_value(key)
        if not isinstance(value, bool):
            raise StatusValueError("The value type should be a bool")
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
