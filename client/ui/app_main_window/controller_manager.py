from __future__ import annotations
from loguru import logger
import collections
import random
import typing
from PySide6.QtCore import QMutex, QMutexLocker, QObject, QThread, Qt, Signal
from controller.general import ControllerGeneralDevice
from .app_context import ApplicationContext
from .status_bar_manager import MainWindowStatusBarManager

import copy


class ControllerManager:
    """控制器管理：连接/断开/重载/重置/命令发送"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        status_bar_manager: MainWindowStatusBarManager,
        controller_event: ControllerEventProxy,
    ):
        # 依赖由组合根注入，不再持有主窗口引用
        # tr 经 context 共享，减少构造参数
        self._context = context
        self.config = context.config
        self.status = context.status
        self.timer = context.timer
        self.status_bar_manager = status_bar_manager
        self.tr = context.tr
        self.controller_event = controller_event

        # 跨 Manager 命令/数据经消息总线，不再在此持有 Mouse/Keyboard 引用

    def init_controller(self):
        device_config: dict = copy.copy(self.config.controller)
        device_config["controller_type"] = self.config.controller["type"]
        device_config["resolution_x"] = self.config.video["resolution_x"]
        device_config["resolution_y"] = self.config.video["resolution_y"]
        device_config["relative_click"] = self.config.mouse["relative_click"]

        self.controller_event.device_init(device_config)

    def connect_controller(self):
        self.init_controller()
        self.controller_command_send("device_open", None)
        self.reload_controller("all")
        self.controller_command_send("keyboard_read", None)
        self._context.event_bus.mouse_capture_triggered.emit()
        check_connection_timer = self.timer.get_exists(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        check_connection_timer.start()

    def disconnect_controller(self):
        check_connection_timer = self.timer.get_exists(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        check_connection_timer.stop()
        self.controller_command_send("device_close", None)

    def reload_controller(self, cmd: str):
        # cmd = ["mouse", "keyboard", "all", "any"]
        if cmd == "mouse":
            self._context.event_bus.clear_mouse_buffer.emit()
        elif cmd == "keyboard":
            self._context.event_bus.clear_keyboard_buffer.emit()
        else:
            self._context.event_bus.clear_mouse_buffer.emit()
            self._context.event_bus.clear_keyboard_buffer.emit()
        self.controller_command_send("device_reload", cmd)

    def reset_controller(self):
        self.controller_command_send("device_reset", None)

    def check_controller_connection(self):
        if self.status.is_enabled("controller"):
            self.controller_command_send("device_check_connection", None)

    def controller_sleep_ms(self, interval: int = 1):
        self.controller_command_send("device_sleep", interval)

    def controller_random_sleep_ms(
        self, min_interval: int = 0, max_interval: int = 100
    ):
        random_time = int(random.uniform(min_interval, max_interval))
        self.controller_sleep_ms(random_time)

    def controller_command_send(self, command: str, data: typing.Any):
        self.controller_event.command_send_signal.emit(command, data)

    def controller_command_reply(
        self, command: str, status_code: int, data: typing.Any
    ):
        ignored_command = [
            "device_reload",
            "device_reset",
            "device_sleep",
            "mouse_relative_write",
            "mouse_absolute_write",
            "keyboard_write",
        ]
        if command == "device_open":
            if status_code == 0:
                # open 成功
                self.status.set_bool("controller", True)
                self.status_bar_manager.show_message(
                    self.tr("Controller connected")
                )
            else:
                self.status.set_bool("controller", False)
                self.status_bar_manager.show_message(
                    self.tr("Controller connect failure")
                )
        elif command == "device_close":
            self.status.set_bool("controller", False)
        elif command == "device_check_connection":
            if status_code != 0:
                # 检查连接返回失败
                self.disconnect_controller()
                self.connect_controller()
        elif command == "keyboard_read":
            if status_code == 0:
                logger.debug("keyboard indicator read succeed")
                self._context.event_bus.keyboard_data_received.emit(data)
            else:
                logger.debug("keyboard indicator read failed")
        elif command in ignored_command:
            pass
        else:
            logger.debug(f"Unhandled command reply: {command}")
            pass


class ControllerEventExecutor(QObject):
    device_execute_signal = Signal()
    device_reply_signal = Signal(str, int, typing.Any)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.device_mutex = QMutex()
        self.deque_mutex = QMutex()
        self.controller_device = ControllerGeneralDevice()
        self.deque: typing.Deque[typing.Tuple[str, typing.Any]] = (
            collections.deque()
        )

        self.device_execute_signal.connect(
            self.device_event_execute, type=Qt.ConnectionType.QueuedConnection
        )
        # reply 预留好了槽
        # 但不需要使用所以暂时注释掉
        # self.device_reply_signal.connect(self.device_reply, type=Qt.ConnectionType.QueuedConnection)

    def device_init(self, buffer: typing.Any) -> bool:
        with QMutexLocker(self.device_mutex):
            self.controller_device.device_init(buffer)
        return True

    def device_close(self) -> None:
        with QMutexLocker(self.device_mutex):
            self.controller_device.device_close()

    def device_event_store(self, command: str, buffer: typing.Any) -> None:
        with QMutexLocker(self.deque_mutex):
            self.deque.append((command, buffer))

    def device_event_execute(self):
        with QMutexLocker(self.deque_mutex):
            try:
                command, buffer = self.deque.popleft()
            except IndexError:
                return
            while len(self.deque) > 0:
                # 如果下一条命令和上一条命令一样切都为 mouse_absolute_write 则可以安全的跳过指令
                if command == "mouse_absolute_write":
                    next_command, next_buffer = self.deque.popleft()
                    if next_command == command:
                        command = next_command
                        buffer = next_buffer
                        continue
                    else:
                        self.deque.appendleft((next_command, next_buffer))
                break
        with QMutexLocker(self.device_mutex):
            status_code: int
            reply: typing.Any
            _, status_code, reply = self.controller_device.device_event(
                command, buffer
            )
            self.device_reply_signal.emit(command, status_code, reply)
        pass

    def device_reply(
        self, command: str, status_code: int, data: typing.Any
    ) -> None:
        pass


class ControllerEventProxy(QObject):
    command_send_signal = Signal(str, typing.Any)
    command_reply_signal = Signal(str, int, typing.Any)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.device_event_executor = ControllerEventExecutor()
        self.execute_thread = QThread()

        self.command_send_signal.connect(self.command_send)
        self.command_reply_signal.connect(self.command_reply)
        self.device_event_executor.device_reply_signal.connect(
            self.command_reply_signal
        )
        self.device_event_executor.moveToThread(self.execute_thread)
        self.execute_thread.start()

    def device_init(self, buffer: typing.Any) -> bool:
        return self.device_event_executor.device_init(buffer)

    def device_close(self) -> None:
        self.device_event_executor.device_close()

    def command_send(self, command: str, buffer: typing.Any) -> None:
        """
        command list:
        "device_open"
        "device_close"
        "device_reload"
        "device_reset"
        "device_sleep"
        "keyboard_read"
        "keyboard_write"
        "mouse_relative_write"
        "mouse_absolute_write"
        """
        # 把命令放入队列
        self.device_event_executor.device_event_store(command, buffer)

        # 执行队列中的一个命令
        self.device_event_executor.device_execute_signal.emit()

    def command_reply(
        self, command: str, status_code: int, data: typing.Any
    ) -> None:
        pass
