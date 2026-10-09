from __future__ import annotations
import typing
from PySide6.QtCore import QEvent
from PySide6.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QWidget

import functools
import platform
import project_var
from PySide6.QtCore import QTranslator
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication

from status_buffer import StatusBuffer
from project_path import (
    project_binary_directory_path,
    project_source_directory_path,
)

from ui.ui_main import MainWindow
from ui.ui_about import AboutDialog
from ui.ui_custom_key import CustomKeyDialog
from ui.ui_indicator_lights import IndicatorLightsDialog
from ui.ui_messagebox import OptionalMessageBox
from ui.ui_paste_board import PasteBoardDialog
from ui.ui_settings import SettingsDialog

from .controller_manager import ControllerEventProxy
from .app_context import QtThreadManager, QtTimerManager
from .keyboard_code_data import KeyboardCodeData
from .video_manager import VideoSession
from .status_bar_manager import MainWindowStatusBarManager
from .app_context import ApplicationContext, WindowService
from .config_manager import ConfigManager
from .icon_manager import IconManager
from .menu_manager import MenuManager
from .controller_manager import ControllerManager
from .keyboard_manager import KeyboardManager
from .mouse_manager import MouseManager
from .video_manager import VideoManager
from .window_manager import WindowManager

# ============================================================
# AppMainWindow - 瘦身协调器/Facade
# ============================================================


class AppMainWindow(MainWindow):
    """主窗口 - 协调器，持有各管理器实例"""

    WINDOW_TITLE: str = "USB KVM Client"
    QT_BASE_TRANSLATOR: QTranslator = QTranslator()
    WINDOW_TRANSLATOR: QTranslator = QTranslator()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._create_infrastructure()

        self._create_ui_objects()

        self._create_managers()

        self._init_ui()

        self._wire_events()

        self._start_services()

    def _create_infrastructure(self) -> None:
        """创建全局基础设施对象"""
        self.status: StatusBuffer = StatusBuffer(
            {
                "screen_height": 0,
                "screen_width": 0,
                "window_width": 0,
                "window_height": 0,
                "camera": False,
                "video_recording": False,
                "controller": False,
                "fullscreen": False,
                "topmost_window": False,
                "keep_aspect_ratio": False,
                "pause_keyboard": False,
                "disable_hotkey": False,
                "quick_paste": True,
                "hook_state": False,
                "pause_mouse": False,
                "mouse_capture": False,
                "relative_mode": False,
                "hide_cursor": False,
                "correction_cursor": False,
                "block_input": False,
            }
        )
        self.child_dialog: list[typing.Any] = []
        self.threads = QtThreadManager()
        self.timer = QtTimerManager()
        self.source_directory: str = project_source_directory_path()
        self.binary_directory: str = project_binary_directory_path()

        # 获取显示器分辨率大小
        desktop_screen = QGuiApplication.primaryScreen()
        self.status.set_number(
            "screen_height", desktop_screen.availableGeometry().height()
        )
        self.status.set_number(
            "screen_width", desktop_screen.availableGeometry().width()
        )

        # 应用上下文（显式传递依赖）；总线在构造时订阅 StatusBuffer，
        # 使其变更经 Qt 信号对外广播
        self._context = ApplicationContext(self.status)
        self._context.config = None  # 稍后设置
        self._context.timer = self.timer
        self._context.threads = self.threads
        self._context.source_directory = self.source_directory
        self._context.binary_directory = self.binary_directory

        # 窗口操作门面：把主窗口的绑定方法集中注入 context，
        # 供各 Manager 经 context.window_service 调用，避免直接持有窗口引用
        self._context.window_service = WindowService(
            is_active_window=self.isActiveWindow,
            geometry=self.geometry,
            size=self.size,
            show_full_screen=self.showFullScreen,
            show_normal=self.showNormal,
            menu_bar=self.menuBar,
            status_bar=self.statusBar,
            window_flags=self.windowFlags,
            window_handle=self.windowHandle,
            frame_geometry=self.frameGeometry,
            move_window=self.move,
            resize_window=self.resize,
            set_central_widget=self.setCentralWidget,
            set_window_title=self.setWindowTitle,
            show_maximized=self.showMaximized,
            take_central_widget=self.takeCentralWidget,
            map_to_global=self.mapToGlobal,
            set_cursor=self.setCursor,
            show_critical=self.show_critical,
            show_optional_information=self.show_optional_information,
            get_save_file_name=self.get_save_file_name,
            window_title=self.WINDOW_TITLE,
        )
        self._context.tr = self.tr

    def _create_ui_objects(self) -> None:
        """创建 UI 对象（对话框/视频控件/事件代理），供各 Manager 注入使用"""
        self.about_dialog = AboutDialog()
        self.custom_key_dialog = CustomKeyDialog()
        self.indicator_lights_dialog = IndicatorLightsDialog()
        self.paste_board_dialog = PasteBoardDialog()
        self.settings_dialog = SettingsDialog()
        self.child_dialog.extend(
            [
                self.about_dialog,
                self.custom_key_dialog,
                self.indicator_lights_dialog,
                self.paste_board_dialog,
                self.settings_dialog,
            ]
        )
        # 视频控件（只创建一次，供 Mouse/Video/Window Manager 共享）
        self.video_widget: QVideoWidget = QVideoWidget()
        self.video_disconnect_label: QLabel = QLabel()
        self.video_session: VideoSession = VideoSession()
        self.controller_event: ControllerEventProxy = ControllerEventProxy()
        self.status_bar_manager = MainWindowStatusBarManager(self.statusbar)

    def _create_managers(self) -> None:
        """创建所有 Manager（依赖全部在组合根显式注入）"""
        self.keyboard_code_data = KeyboardCodeData()

        # 配置管理器（最先创建，配置是其他管理器的共同依赖）
        self.config_manager = ConfigManager(
            self._context,
            qt_base_translator=self.QT_BASE_TRANSLATOR,
            window_translator=self.WINDOW_TRANSLATOR,
            child_dialog=self.child_dialog,
            retranslate_ui=functools.partial(self.retranslateUi, self),
        )
        self.config_manager.load_config()
        self.config = self._context.config
        # 共享配置管理器（供各 Manager 经 context 访问，减少构造参数）
        self._context.config_manager = self.config_manager

        # 图标服务（无状态）
        self.icon_manager = IconManager(self.source_directory)

        self.controller_manager = ControllerManager(
            self._context,
            status_bar_manager=self.status_bar_manager,
            controller_event=self.controller_event,
        )

        self.keyboard_manager = KeyboardManager(
            self._context,
            controller_manager=self.controller_manager,
            status_bar_manager=self.status_bar_manager,
            keyboard_code_data=self.keyboard_code_data,
            custom_key_dialog=self.custom_key_dialog,
            indicator_lights_dialog=self.indicator_lights_dialog,
        )

        # 鼠标管理器（video_manager 在视频管理器创建后后置装配，见下）
        self.mouse_manager = MouseManager(
            self._context,
            controller_manager=self.controller_manager,
            status_bar_manager=self.status_bar_manager,
            video_manager=None,
        )

        # 视频管理器（窗口操作统一经 context.window_service，不再接收窗口绑定方法）
        self.video_manager = VideoManager(
            self._context,
            mouse_manager=self.mouse_manager,
            icon_service=self.icon_manager,
            video_widget=self.video_widget,
            video_disconnect_label=self.video_disconnect_label,
            video_session=self.video_session,
        )
        # 双向依赖通过组合根后置装配（避免构造期循环引用）
        self.mouse_manager.video_manager = self.video_manager

        # 窗口管理器（窗口操作/翻译/配置均经 context 获取，参数大幅精简）
        self.window_manager = WindowManager(
            self._context,
            video_manager=self.video_manager,
            controller_manager=self.controller_manager,
            mouse_manager=self.mouse_manager,
            keyboard_manager=self.keyboard_manager,
            status_bar_manager=self.status_bar_manager,
            settings_dialog=self.settings_dialog,
        )

        self.menu_manager = MenuManager(
            self._context,
            menu_shortcut_keys=self.menu_shortcut_keys,
            custom_key_dialog=self.custom_key_dialog,
            indicator_lights_dialog=self.indicator_lights_dialog,
            keyboard_manager=self.keyboard_manager,
            controller_manager=self.controller_manager,
            controller_event=self.controller_event,
        )

    def show_critical(self, title: str, text: str) -> None:
        """错误提示框；以主窗口作为 Qt 对话框父级（唯一需要窗口句柄的场合）"""
        QMessageBox.critical(
            self,
            title,
            text,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.NoButton,
        )

    def show_optional_information(
        self, title: str, text: str, checkbox_text: str
    ) -> bool:
        """带『不再提示』复选框的提示框，返回用户是否勾选了不再提示"""
        _, close_next_tip = OptionalMessageBox.optional_information(
            self,
            title,
            text,
            checkbox_text,
            False,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.NoButton,
        )
        return close_next_tip

    def get_save_file_name(
        self, caption: str, default_name: str, file_filter: str
    ) -> str:
        """另存为文件对话框，返回用户选择的完整路径（取消时为空字符串）"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, caption, default_name, file_filter
        )
        return file_name

    ######################################################################
    # 覆盖窗口事件（必须定义在 QWidget 子类上，Qt 事件才会分发到这里）
    ######################################################################

    # 鼠标移动事件
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self.mouse_manager.handle_mouse_move_event(event)

    # 鼠标按下事件
    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        self.mouse_manager.handle_mouse_press_event(event)

    # 鼠标松开事件
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.mouse_manager.handle_mouse_release_event(event)

    # 鼠标滚动事件
    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        self.mouse_manager.handle_mouse_wheel_event(event)

    # 键盘按下事件
    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        self.keyboard_manager.handle_key_press_with_event(event)

    # 键盘松开事件
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)
        self.keyboard_manager.handle_key_release_event(event)

    # 窗口改变事件（构造期间 setupUi 触发 setWindowTitle 也会收到该事件，此时 Manager 尚未创建）
    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if hasattr(self, "window_manager"):
            self.window_manager.handle_change_event(event)

    # 窗口尺寸改变：仅把尺寸写回 StatusBuffer，绝不移动窗口
    # （满足“缩放过程中不动”的要求；位置信息由 get_mouse_mapping_geometry 自行负责）
    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "status"):
            self.status.set_number("window_width", self.width())
            self.status.set_number("window_height", self.height())

    # 关闭事件
    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        self.window_manager.handle_close_event()

    def _init_ui(self) -> None:
        """UI 初始化（依赖已创建完成的各 Manager）"""
        # 刷新 ui 语言翻译
        self.config_manager.refresh_translate()
        # 加载窗口图标
        self.icon_manager.init_window_icon(self.setWindowIcon)
        # 加载菜单图标（动作与图标的对应关系在组合根显式给出）
        self.icon_manager.init_menu_icon(
            [
                (self.action_device_connect, "connect.png"),
                (self.action_device_disconnect, "disconnect.png"),
                (self.action_device_reload, "reload.png"),
                (self.action_device_reset, "reset.png"),
                (self.action_settings, "setting.png"),
                (self.action_minimize, "window-minimize.png"),
                (self.action_maximize, "window-maximize.png"),
                (self.action_normal_size, "window-normal-size.png"),
                (self.action_exit, "window-close.png"),
                (self.action_fullscreen, "fullscreen.png"),
                (self.action_resize_window, "resize.png"),
                (self.action_topmost, "topmost.png"),
                (self.action_keep_aspect_ratio, "ratio.png"),
                (self.action_capture_image, "capture.png"),
                (self.action_record_video, "record.png"),
                (self.action_pause_keyboard, "pause.png"),
                (self.action_reload_keyboard, "reload.png"),
                (self.menu_shortcut_keys, "keyboard-outline.png"),
                (self.action_custom_key, "keyboard-settings-outline.png"),
                (self.action_disable_hotkey, "hotkey.png"),
                (self.action_paste_board, "paste.png"),
                (self.action_quick_paste, "quick_paste.png"),
                (self.action_system_hook, "hook.png"),
                (self.action_sync_indicator, "sync.png"),
                (self.action_indicator_light, "capslock.png"),
                (self.action_pause_mouse, "pause.png"),
                (self.action_reload_mouse, "reload.png"),
                (self.action_capture_mouse, "mouse.png"),
                (self.action_release_mouse, "mouse-off.png"),
                (self.action_relative_mouse, "relative.png"),
                (self.action_hide_cursor, "cursor.png"),
                (self.action_correction_cursor, "cursor-correction.png"),
                (self.action_open_windows_device_manager, "device.png"),
                (self.action_open_on_screen_keyboard, "keyboard-variant.png"),
                (self.action_open_calculator, "calculator.png"),
                (self.action_open_snipping_tool, "monitor-screenshot.png"),
                (self.action_open_notepad, "notebook-edit.png"),
                (self.action_about, "python.png"),
                (self.action_about_qt, "qt.png"),
                (self.action_debug_mode, "debug.png"),
            ]
        )
        self._init_sub_window_icon()
        # 初始化快捷键菜单
        self.menu_manager.init_shortcut_keys_menu()
        # 菜单初始状态设定
        self.menu_manager.init_menu_checked_state()
        # 初始化 video widget（控件已在 _create_ui_objects 创建）
        self.video_manager.init_video_widget()
        # 初始化控制器（事件代理已注入）
        self.controller_manager.init_controller()
        controller_event_thread = self.threads.create("CONTROLLER_EVENT_THREAD")
        controller_event_thread.start()
        self.controller_event.moveToThread(controller_event_thread)

    def _init_sub_window_icon(self) -> None:
        """设置子窗口图标（原 IconManager.init_sub_window_icon 的逻辑移至此）"""
        self.about_dialog.setWindowIcon(
            self.icon_manager.load_icon("python.png")
        )
        self.custom_key_dialog.setWindowIcon(
            self.icon_manager.load_icon("keyboard-outline.png")
        )
        self.indicator_lights_dialog.setWindowIcon(
            self.icon_manager.load_icon("capslock.png")
        )
        self.paste_board_dialog.setWindowIcon(
            self.icon_manager.load_icon("paste.png")
        )
        self.settings_dialog.setWindowIcon(
            self.icon_manager.load_icon("setting.png")
        )

    def _wire_events(self) -> None:
        """信号接线：连接各 Manager 之间的事件

        键盘热键动作（Ctrl+Alt+F11/F12 等）现已通过消息总线
        (AppEventBus.hotkey_action_triggered) 广播，WindowManager 在构造时
        已订阅，故此处不再需要运行期补注入。

        菜单 QAction 的接线与初始勾选状态统一收口到组合根。
        A 类（action.triggered → manager.handler）不走事件总线：
        其为 1:1 定向命令，总线仅承载一对多广播（见 AppEventBus 设计边界）。
        """
        # 订阅 StatusBuffer 变更，统一把状态回写到菜单/工具栏 QAction
        # （B 类状态回写：Manager 只写 StatusBuffer，组合根在此映射回 UI
        self._context.event_bus.status_changed.connect(self._on_status_changed)
        self._sync_action_states_from_status()

        # 菜单动作信号接线（A 类：组合根统一接线，Manager 仅暴露 handler 方法）
        # 表驱动：每项 (QAction, 目标可调用对象)；带参/对话框等特例用 lambda。
        for action, slot in (
            (self.action_device_connect, self.window_manager.connect_devices),
            (
                self.action_device_disconnect,
                self.window_manager.disconnect_devices,
            ),
            (self.action_device_reload, self.window_manager.reload_devices),
            (self.action_device_reset, self.window_manager.reset_devices),
            (self.action_settings, self.window_manager.execute_settings_dialog),
            (self.action_minimize, self.showMinimized),
            (self.action_maximize, self.showMaximized),
            (self.action_normal_size, self.showNormal),
            (self.action_exit, self.close),
            (
                self.action_fullscreen,
                self.window_manager.fullscreen_state_toggle,
            ),
            (
                self.action_resize_window,
                self.window_manager.resize_window_with_video_resolution,
            ),
            (
                self.action_topmost,
                self.window_manager.window_topmost_state_toggle,
            ),
            (
                self.action_keep_aspect_ratio,
                self.window_manager.keep_aspect_ratio_toggle,
            ),
            (
                self.action_capture_image,
                self.window_manager.image_capture_triggered,
            ),
            (
                self.action_record_video,
                self.window_manager.video_record_triggered,
            ),
            (
                self.action_pause_keyboard,
                self.window_manager.sync_pause_keyboard_state,
            ),
            (
                self.action_reload_keyboard,
                lambda: self.controller_manager.reload_controller("keyboard"),
            ),
            (
                self.action_custom_key,
                self.keyboard_manager.custom_key_dialog_show,
            ),
            (
                self.action_disable_hotkey,
                self.keyboard_manager.disable_hotkey_triggered,
            ),
            (self.action_paste_board, lambda: self.paste_board_dialog.exec()),
            (self.action_quick_paste, self.keyboard_manager.quick_paste_toggle),
            (
                self.action_indicator_light,
                self.keyboard_manager.execute_indicator_lights_dialog,
            ),
            (
                self.action_system_hook,
                self.keyboard_manager.system_hook_triggered,
            ),
            (
                self.action_sync_indicator,
                self.keyboard_manager.sync_indicator_triggered,
            ),
            (
                self.action_pause_mouse,
                self.window_manager.sync_pause_mouse_state,
            ),
            (
                self.action_reload_mouse,
                lambda: self.controller_manager.reload_controller("mouse"),
            ),
            (
                self.action_capture_mouse,
                self.mouse_manager.mouse_capture_triggered,
            ),
            (
                self.action_release_mouse,
                self.mouse_manager.mouse_capture_release_triggered,
            ),
            (
                self.action_relative_mouse,
                self.mouse_manager.mouse_relative_mode_triggered,
            ),
            (
                self.action_hide_cursor,
                self.mouse_manager.mouse_hide_cursor_triggered,
            ),
            (
                self.action_correction_cursor,
                self.mouse_manager.mouse_cursor_correction_triggered,
            ),
            (
                self.action_open_windows_device_manager,
                lambda: self.window_manager.menu_tools_actions("devmgmt.msc"),
            ),
            (
                self.action_open_on_screen_keyboard,
                lambda: self.window_manager.menu_tools_actions("osk"),
            ),
            (
                self.action_open_calculator,
                lambda: self.window_manager.menu_tools_actions("calc"),
            ),
            (
                self.action_open_snipping_tool,
                lambda: self.window_manager.menu_tools_actions("snipping_tool"),
            ),
            (
                self.action_open_notepad,
                lambda: self.window_manager.menu_tools_actions("notepad"),
            ),
            (self.action_about, lambda: self.about_dialog.exec()),
            (self.action_about_qt, lambda: QApplication.aboutQt()),
            (self.action_debug_mode, self.window_manager.switch_debug_mode),
        ):
            action.triggered.connect(slot)

        # 菜单所属对话框信号接线（非 action，原在 MenuManager.init_menu_connect_signal）
        self.custom_key_dialog.custom_key_send_signal.connect(
            self.keyboard_manager.custom_key_send
        )
        self.custom_key_dialog.custom_key_save_signal.connect(
            self.keyboard_manager.custom_key_save
        )
        self.paste_board_dialog.send_string_signal.connect(
            self.keyboard_manager.keyboard_send_string
        )

        # 其它跨 Manager 信号接线（由 MenuManager 协调）
        self.menu_manager.init_connect_signal()

    def _on_status_changed(self, key: str, value: typing.Any) -> None:
        """StatusBuffer -> QAction 状态回写（B 类解耦的核心映射）。

        Manager 只写 StatusBuffer；此处把状态键映射到对应 QAction 的
        setChecked / setEnabled / setText，组合根成为唯一操作 UI 元素的地方。
        """
        if key == "fullscreen":
            self.action_fullscreen.setChecked(value)
            self.action_resize_window.setEnabled(not value)
        elif key == "topmost_window":
            self.action_topmost.setChecked(value)
        elif key == "keep_aspect_ratio":
            self.action_keep_aspect_ratio.setChecked(value)
        elif key == "video_recording":
            self.action_record_video.setChecked(value)
            self.action_record_video.setText(
                self.tr("Stop recording") if value else self.tr("Record video")
            )
        elif key == "pause_keyboard":
            self.action_pause_keyboard.setChecked(value)
        elif key == "pause_mouse":
            self.action_pause_mouse.setChecked(value)
        elif key == "relative_mode":
            self.action_relative_mouse.setChecked(value)
        elif key == "hide_cursor":
            self.action_hide_cursor.setChecked(value)
        elif key == "correction_cursor":
            self.action_correction_cursor.setChecked(value)
        elif key == "disable_hotkey":
            self.action_disable_hotkey.setChecked(value)
        elif key == "quick_paste":
            self.action_quick_paste.setChecked(value)
        elif key == "hook_state":
            self.action_system_hook.setChecked(value)

    def _sync_action_states_from_status(self) -> None:
        """构造完成后，按当前 StatusBuffer 一次性同步所有 QAction 初始状态。

        debug_mode 为全局变量（非 StatusBuffer），单独按 project_var 同步。
        """
        for key in (
            "fullscreen",
            "topmost_window",
            "keep_aspect_ratio",
            "video_recording",
            "pause_keyboard",
            "pause_mouse",
            "relative_mode",
            "hide_cursor",
            "correction_cursor",
            "disable_hotkey",
            "quick_paste",
            "hook_state",
        ):
            self._on_status_changed(key, self.status.is_enabled(key))
        self.action_debug_mode.setChecked(project_var.debug_mode)

    def _start_services(self) -> None:
        """启动后台服务（定时器、自动连接等）"""
        # 每秒自动检查控制器连接
        controller_check_connection_timer = self.timer.create(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        controller_check_connection_timer.timeout.connect(
            self.controller_manager.check_controller_connection
        )
        controller_check_connection_timer.setInterval(1000)

        # 鼠标报告定时器
        mouse_report_timer = self.timer.create("MOUSE_REPORT_TIMER")
        mouse_report_timer.timeout.connect(
            self.mouse_manager.mouse_report_timer_triggered
        )
        mouse_report_timer.start(self.mouse_manager.mouse_report_interval)
        self.mouse_manager.update_mouse_report_frequency()

        # 全屏事件定时器
        fullscreen_event_timer = self.timer.create("FULLSCREEN_EVENT_TIMER")
        fullscreen_event_timer.timeout.connect(
            self.window_manager.execute_fullscreen_event_command
        )

        # 键盘钩子（钩子对象由 KeyboardManager 自己持有）
        if platform.system() == "Windows":
            self.keyboard_manager.init_system_hook()

        # Window accept mouse events
        self.setMouseTracking(True)

        # 显示操作系统警告
        self.window_manager.tips_system_warning()
        # 启动自动连接
        self.window_manager.auto_connect_on_startup()
