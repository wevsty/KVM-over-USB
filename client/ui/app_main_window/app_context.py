from __future__ import annotations
import typing
from PySide6.QtCore import QObject, QThread, QTimer, Signal

from project_config import MainConfig
from status_buffer import StatusBuffer


class QtThreadManager:
    def __init__(self):
        self.threads: dict[str, QThread] = dict()

    def create(self, thread_name: str) -> QThread:
        thread_object = QThread()
        self.threads[thread_name] = thread_object
        return thread_object

    def get(self, thread_name: str) -> QThread | None:
        thread_object = self.threads.get(thread_name, None)
        return thread_object

    def get_exists(self, thread_name: str) -> QThread:
        thread_object = self.threads.get(thread_name, None)
        if thread_object is None:
            raise KeyError(f"thread {thread_name} not exists")
        return thread_object

    def delete(self, thread_name: str) -> None:
        self.threads.pop(thread_name, None)

    def quit(self, thread_name: str) -> None:
        thread_object = self.threads.get(thread_name, None)
        if thread_object is None:
            return
        if thread_object.isRunning():
            thread_object.quit()
            thread_object.wait()
        return

    def quit_all(self) -> None:
        for _, thread_object in self.threads.items():
            if thread_object.isRunning():
                thread_object.quit()
                thread_object.wait()


class QtTimerManager:
    def __init__(self):
        self.timers: dict[str, QTimer] = dict()

    def create(self, timer_name: str) -> QTimer:
        timer_object = QTimer()
        self.timers[timer_name] = timer_object
        return timer_object

    def get(self, timer_name: str) -> QTimer | None:
        timer_object = self.timers.get(timer_name, None)
        return timer_object

    def get_exists(self, timer_name: str) -> QTimer:
        timer_object = self.timers.get(timer_name, None)
        if timer_object is None:
            raise KeyError(f"timer {timer_name} not exists")
        return timer_object

    def delete(self, timer_name: str) -> None:
        self.timers.pop(timer_name, None)

    def quit(self, timer_name: str) -> None:
        timer_object = self.timers.get(timer_name, None)
        if timer_object is None:
            return
        if timer_object.isActive():
            timer_object.stop()
        return

    def quit_all(self) -> None:
        for _, timer_object in self.timers.items():
            if timer_object.isActive():
                timer_object.stop()


class AppEventBus(QObject):
    """应用级消息总线（事件总线）。

    仅承载『一对多、无返回值』的广播通知类事件，用于解耦原本需要互相
    持有引用（或在组合根运行期打补丁）的 Manager。

    设计边界（重要）：
    - 适合：状态/事件变化后『请相关方自行刷新』的通知（如热键动作、
      快捷键配置变更、状态缓冲变更）。
    - 不适合：需要共享可变状态（缓冲区）、或要求返回值/携带特定对象
      的 1:1 服务调用（如对话框居中、缓冲区读写）。后者仍走显式依赖或
      门面对象（Facade），不在此定义。
    - 新增事件时，请确认它属于『广播通知』而非『定向命令』。
    """

    # 键盘自注册热键触发（Ctrl+Alt+F11 退出全屏 / F12 释放鼠标捕获）
    # payload: 动作名字符串，由 WindowManager 解释执行
    hotkey_action_triggered = Signal(str)

    # 自定义快捷键被保存，菜单需重建快捷键子菜单
    shortcut_keys_changed = Signal()

    # 控制器请求鼠标管理器开始捕获（ControllerManager → MouseManager）
    mouse_capture_triggered = Signal()
    # 控制器请求清空鼠标缓冲区（ControllerManager → MouseManager）
    clear_mouse_buffer = Signal()
    # 控制器请求清空键盘缓冲区（ControllerManager → KeyboardManager）
    clear_keyboard_buffer = Signal()
    # 控制器读到键盘指示灯数据，交由键盘管理器写入缓冲区并刷新状态栏
    # payload: 设备返回数据（ControllerManager → KeyboardManager）
    keyboard_data_received = Signal(object)
    # 键盘管理器请求将对话框居中（KeyboardManager → WindowManager）
    # payload: 需居中的 QDialog
    move_dialog_to_center = Signal(object)

    # 共享状态 StatusBuffer 变更通知（key, value）
    # 由本总线在构造时订阅 StatusBuffer 的观察者并翻译为 Qt 信号；
    # StatusBuffer 本身保持纯 Python（无 Qt 依赖），仅在此处被桥接一次。
    status_changed = Signal(str, object)

    def __init__(self, status: StatusBuffer, parent: QObject | None = None):
        super().__init__(parent)
        # 把 StatusBuffer 的纯 Python 观察者桥接进本总线的 Qt 信号（仅此一处）
        status.add_change_listener(self.status_changed.emit)

    def on_status(
        self, key: str, cb: typing.Callable[[typing.Any], None]
    ) -> None:
        """按 key 精准订阅 StatusBuffer 变更，省去各消费者自行 if/elif 过滤。

        与通用信号 status_changed(key, value) 互补：UI 状态键仍由门面集中
        映射到 QAction；数据键（如窗口尺寸）可经此方法让特定 Manager 精准消费。
        """
        self.status_changed.connect(lambda k, v: cb(v) if k == key else None)


class WindowService:
    """窗口操作门面（Facade）。

    把主窗口的绑定方法集中注入，供各 Manager 经 context 调用，
    避免 Manager 直接持有主窗口引用。对应 AppEventBus 设计边界中
    『定向命令走门面对象』的约定。组合根在创建主窗口后实例化本类。
    """

    def __init__(
        self,
        *,
        is_active_window: typing.Callable[[], bool],
        geometry: typing.Callable[[], typing.Any],
        size: typing.Callable[[], typing.Any],
        show_full_screen: typing.Callable[[], None],
        show_normal: typing.Callable[[], None],
        menu_bar: typing.Callable[[], typing.Any],
        status_bar: typing.Callable[[], typing.Any],
        window_flags: typing.Callable[[], typing.Any],
        window_handle: typing.Callable[[], typing.Any],
        frame_geometry: typing.Callable[[], typing.Any],
        move_window: typing.Callable[[typing.Any], None],
        resize_window: typing.Callable[[int, int], None],
        set_central_widget: typing.Callable[[typing.Any], None],
        set_window_title: typing.Callable[[str], None],
        show_maximized: typing.Callable[[], None],
        take_central_widget: typing.Callable[[], typing.Any],
        map_to_global: typing.Callable[[typing.Any], typing.Any],
        set_cursor: typing.Callable[[typing.Any], None],
        show_critical: typing.Callable[[str, str], None],
        show_optional_information: typing.Callable[[str, str, str], bool],
        get_save_file_name: typing.Callable[[str, str, str], str],
        window_title: str,
    ):
        self.is_active_window = is_active_window
        self.geometry = geometry
        self.size = size
        self.show_full_screen = show_full_screen
        self.show_normal = show_normal
        self.menu_bar = menu_bar
        self.status_bar = status_bar
        self.window_flags = window_flags
        self.window_handle = window_handle
        self.frame_geometry = frame_geometry
        self.move_window = move_window
        self.resize_window = resize_window
        self.set_central_widget = set_central_widget
        self.set_window_title = set_window_title
        self.show_maximized = show_maximized
        self.take_central_widget = take_central_widget
        self.map_to_global = map_to_global
        self.set_cursor = set_cursor
        self.show_critical = show_critical
        self.show_optional_information = show_optional_information
        self.get_save_file_name = get_save_file_name
        self.window_title = window_title


class ApplicationContext:
    """全局应用上下文，持有所有 Manager 共享的基础设施与消息总线"""

    def __init__(self, status: StatusBuffer):
        self.config: MainConfig | None = None
        self.status: StatusBuffer = status
        self.timer: QtThreadManager | None = None
        self.threads: QtThreadManager | None = None
        self.source_directory: str = ""
        self.binary_directory: str = ""
        # 应用级消息总线（共享服务，构造期注入，所有 Manager 经 context 访问）
        # 总线在构造时订阅 StatusBuffer，使其变更经 Qt 信号对外广播
        self.event_bus: AppEventBus = AppEventBus(status)
        # 窗口操作门面（组合根创建主窗口后注入）
        self.window_service: WindowService | None = None
        # 共享服务（组合根注入）
        self.config_manager: typing.Any = None
        # 翻译函数（组合根注入，默认透传）
        self.tr: typing.Callable[..., str] = lambda s, *args: str(s)
