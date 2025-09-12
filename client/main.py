import argparse
import collections
import copy
import ctypes
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import typing

from PySide6.QtCore import (
    QEvent,
    QMutex,
    QMutexLocker,
    QObject,
    QPoint,
    QSize,
    Qt,
    QThread,
    QTimer,
    QTranslator,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QCloseEvent,
    QCursor,
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QSurfaceFormat,
    QWheelEvent,
)
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QImageCapture,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
    QVideoFrame,
    QVideoSink,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QLabel,
    QMessageBox,
    QStatusBar,
    QWidget,
)
from loguru import logger

import keyboard_buffer
import project_var
from controller.general import ControllerGeneralDevice
from data.keyboard_key_name_to_hid_code import KEY_NAME_TO_HID_CODE
from data.keyboard_os_key_code_to_hid_code import (
    qt_key_event_to_hid_code,
    os_scancode_code_to_hid_code,
)
from data.keyboard_shift_symbol import SHIFT_SYMBOL
from keyboard_buffer import (
    KeyboardIndicatorBuffer,
    KeyboardKeyBuffer,
    KeyStateEnum,
)
from mouse_buffer import (
    MouseButtonCodeEnum,
    MouseButtonStateEnum,
    MouseStateBuffer,
    MouseWheelStateEnum,
)
from project_config import MainConfig
from project_info import CONFIG_VERSION_STRING
from project_path import (
    project_binary_directory_path,
    project_source_directory_path,
)
from status_buffer import StatusBuffer
from ui.ui_about import AboutDialog
from ui.ui_custom_key import CustomKeyDialog
from ui.ui_indicator_lights import IndicatorLightsDialog
from ui.ui_main import MainWindow
from ui.ui_messagebox import MessageBox
from ui.ui_paste_board import PasteBoardDialog
from ui.ui_settings import SettingsDialog

# 特定系统依赖
if platform.system() == "Windows":
    import pythoncom
    import pyWinhook as pyHook


class ControllerEventProxy(QObject):
    command_send_signal = Signal(str, object)
    command_reply_signal = Signal(str, int, object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.mutex = QMutex()
        self.mutex_locker = QMutexLocker(self.mutex)
        self.controller_device = ControllerGeneralDevice()
        self.command_send_signal.connect(self.command_send)
        self.command_reply_signal.connect(self.command_reply)

    def device_init(self, buffer: typing.Any) -> bool:
        with self.mutex_locker:
            self.controller_device.device_init(buffer)
        return True

    def command_send(
        self, command: str, buffer: object
    ) -> tuple[str, int, object]:
        """
        command list:
        "device_open"
        "device_close"
        "device_check"
        "device_reload"
        "device_reset"
        "keyboard_read"
        "keyboard_write"
        "mouse_relative_write"
        "mouse_absolute_write"
        """
        status_code: int = 1
        reply = None
        with self.mutex_locker:
            _, status_code, reply = self.controller_device.device_event(
                command, buffer
            )
            self.command_reply_signal.emit(command, status_code, reply)
        return command, status_code, reply

    def command_reply(self, command: str, status: int, data: object):
        pass


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


class KeyboardCodeData:
    def __init__(self):
        # dict[key_name, hid_code]
        self.key_name_to_hid_code: dict[str, int] = dict()
        # 载入数据
        self.load_keyboard_code_data()

    # 载入键盘代码数据
    def load_keyboard_code_data(self):
        self.key_name_to_hid_code = KEY_NAME_TO_HID_CODE

    # 转换 scan code 到 hid code
    @staticmethod
    def convert_scan_code_to_hid_code(scancode: int) -> tuple[bool, int]:
        status, hid_code = os_scancode_code_to_hid_code(scancode)
        if not status:
            logger.warning(f"Unknown keyboard scancode: {scancode}")
        return status, hid_code

    # 转换 QKeyEvent 为 hid code
    @staticmethod
    def convert_qt_key_event_to_hid_code(event: QKeyEvent) -> tuple[bool, int]:
        status, hid_code = qt_key_event_to_hid_code(event)
        if not status:
            logger.warning(
                f"Unknown keyboard key: "
                f"nativeScanCode={event.nativeScanCode()}"
                f"nativeVirtualKey={event.nativeVirtualKey()}"
                f"KeyValue={event.key()}"
            )
        return status, hid_code

    # 转换 key name 到 hid code
    def convert_key_name_to_hid_code(self, key_name: str) -> tuple[bool, int]:
        status: bool = False
        hid_code: int | None = self.key_name_to_hid_code.get(key_name, None)
        if hid_code is None:
            logger.warning(f"Unknown key name: {key_name}")
            hid_code = 0
            return status, hid_code
        else:
            status = True
        return status, hid_code


class VideoSession(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.parent: QObject | None = parent
        self.device: QMediaDevices | None = None
        self.camera: QCamera | None = None
        self.video_sink: QVideoSink | None = None
        self.capture_session: QMediaCaptureSession | None = None
        self.image_capture: QImageCapture | None = None
        self.video_record: QMediaRecorder | None = None

    # 按照视频设备描述返回设备对象
    @staticmethod
    def get_video_device(device_description: str) -> QCameraDevice | None:
        cameras: list[QCameraDevice] = QMediaDevices.videoInputs()
        video_device: QCameraDevice | None = None
        for camera in cameras:
            if camera.description() == device_description:
                video_device = camera
                break
        return video_device

    # 根据配置设置相机格式
    def set_camera_format_with_config(
        self, config: dict[str, typing.Any]
    ) -> bool:
        setting_done = False
        for camera_format in self.device.videoFormats():
            resolution_x = camera_format.resolution().width()
            resolution_y = camera_format.resolution().height()
            pixel_format = camera_format.pixelFormat().name.split("_")[1]
            if (
                resolution_x == config["resolution_x"]
                and resolution_y == config["resolution_y"]
                and pixel_format == config["format"]
            ):
                self.camera.setCameraFormat(camera_format)
                setting_done = True
                break
        return setting_done

    # 根据配置初始化视频设备
    def init_video_device_with_config(
        self, config: dict[str, typing.Any]
    ) -> None:
        # 获得设备名
        device_description = config["device"]
        if device_description == "":
            raise RuntimeError(self.tr("Target video device is empty."))
        self.device = self.get_video_device(device_description)
        if self.device is None:
            raise RuntimeError(self.tr("Target video device not found."))
        # 设置摄像头配置
        self.camera = QCamera(self.device)
        status = self.set_camera_format_with_config(config)
        if not status:
            raise RuntimeError(
                self.tr("Unsupported combination of resolution or format")
            )

    def init_capture_session_with_config(
        self, config: dict[str, typing.Any]
    ) -> None:
        # 设置视频捕捉
        self.capture_session = QMediaCaptureSession()
        self.video_sink = QVideoSink()
        self.image_capture = QImageCapture(self.camera)
        self.video_record = QMediaRecorder(self.camera)

        # capture_session 设定
        self.capture_session.setCamera(self.camera)
        self.capture_session.setVideoSink(self.video_sink)
        self.capture_session.setImageCapture(self.image_capture)
        self.capture_session.setRecorder(self.video_record)

        # image_capture 设定
        self.image_capture.setQuality(QImageCapture.Quality.VeryHighQuality)
        self.image_capture.setFileFormat(QImageCapture.FileFormat.PNG)

        # recorder 设定
        self.video_record.setQuality(QMediaRecorder.Quality[config["quality"]])
        self.video_record.setMediaFormat(QMediaFormat.FileFormat.MPEG4)
        self.video_record.setEncodingMode(
            QMediaRecorder.EncodingMode[config["encoding_mode"]]
        )
        self.video_record.setVideoBitRate(config["encoding_bitrate"])
        self.video_record.setVideoFrameRate(config["frame_rate"])
        self.video_record.setVideoResolution(QSize())


class MainWindowStatusBarManager:
    def __init__(self, status_bar: QStatusBar):
        self.status_bar_labels: collections.OrderedDict[str, QLabel] = (
            collections.OrderedDict()
        )
        self.keyboard_hid_code_data = KeyboardCodeData()
        self.current_message: str = ""
        self.status_bar: QStatusBar = status_bar
        self.init_status_bar()

    def init_status_bar(self) -> None:
        self.init_labels()
        # 设置样式
        self.status_bar.setStyleSheet("padding: 0px;")
        # 设置分割线
        self.status_bar.addPermanentWidget(QLabel())
        # 把 labels 加入状态栏
        for _, label_object in self.status_bar_labels.items():
            self.status_bar.addPermanentWidget(label_object)
        # 增加一个空 label 占位
        self.status_bar.addPermanentWidget(QLabel())
        self.status_bar.reformat()

    def init_labels(self) -> None:
        self.status_bar_labels["CTRL"] = QLabel()
        self.status_bar_labels["SHIFT"] = QLabel()
        self.status_bar_labels["ALT"] = QLabel()
        self.status_bar_labels["META"] = QLabel()
        self.status_bar_labels["CAPS_LOCK"] = QLabel()
        self.status_bar_labels["NUM_LOCK"] = QLabel()
        self.status_bar_labels["SCR_LOCK"] = QLabel()

        # 设置显示文字
        self.status_bar_labels["CTRL"].setText("CTRL")
        self.status_bar_labels["SHIFT"].setText("SHIFT")
        self.status_bar_labels["ALT"].setText("ALT")
        self.status_bar_labels["META"].setText("META")
        self.status_bar_labels["CAPS_LOCK"].setText("CAPS")
        self.status_bar_labels["NUM_LOCK"].setText("NUM")
        self.status_bar_labels["SCR_LOCK"].setText("SCR")

        # 设置字体
        font = QFont()
        font.setBold(True)
        # font.setPointSize(10)

        for _, label_object in self.status_bar_labels.items():
            # 设置字体
            label_object.setFont(font)
            # 设置样式
            label_object.setStyleSheet("color: grey")
            # 设置聚焦方式
            label_object.setFocusPolicy(Qt.NoFocus)

    def get(self) -> QStatusBar:
        return self.status_bar

    # 设置 label 指示状态
    def update_label_indication_status(self, label_name: str, enable: bool):
        if enable:
            self.status_bar_labels[label_name].setStyleSheet("color: black")
        else:
            self.status_bar_labels[label_name].setStyleSheet("color: grey")

    # 通过键盘缓冲区更新 label 显示
    def update_label_status(
        self,
        key_buffer: keyboard_buffer.KeyboardKeyBuffer,
        indication_buffer: keyboard_buffer.KeyboardIndicatorBuffer,
    ):
        _, ctrl_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "ctrl_left"
        )
        _, ctrl_right = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "ctrl_right"
            )
        )
        if key_buffer.is_pressed(ctrl_left) or key_buffer.is_pressed(
            ctrl_right
        ):
            self.update_label_indication_status("CTRL", True)
        else:
            self.update_label_indication_status("CTRL", False)

        _, shift_left = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "shift_left"
            )
        )
        _, shift_right = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "shift_right"
            )
        )
        if key_buffer.is_pressed(shift_left) or key_buffer.is_pressed(
            shift_right
        ):
            self.update_label_indication_status("SHIFT", True)
        else:
            self.update_label_indication_status("SHIFT", False)

        _, alt_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "alt_left"
        )
        _, alt_right = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "alt_right"
        )
        if key_buffer.is_pressed(alt_left) or key_buffer.is_pressed(alt_right):
            self.update_label_indication_status("ALT", True)
        else:
            self.update_label_indication_status("ALT", False)

        _, win_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "win_left"
        )
        _, win_right = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "win_right"
        )
        if key_buffer.is_pressed(win_left) or key_buffer.is_pressed(win_right):
            self.update_label_indication_status("META", True)
        else:
            self.update_label_indication_status("META", False)

        self.update_label_indication_status(
            "CAPS_LOCK", indication_buffer.caps_lock
        )
        self.update_label_indication_status(
            "NUM_LOCK", indication_buffer.num_lock
        )
        self.update_label_indication_status(
            "SCR_LOCK", indication_buffer.scroll_lock
        )

    def show_message(self, text: str):
        if not self.current_message == text:
            self.status_bar.showMessage(text)
        else:
            self.current_message = text


class AppMainWindow(MainWindow):
    # 窗口标题
    WINDOW_TITLE: str = "USB KVM Client"

    def __init__(self, parent: QWidget | None = None):
        # 初始化父类
        super().__init__(parent)

        # 初始化状态
        self.status = StatusBuffer()
        self.status = StatusBuffer(
            {
                "screen_height": 0,
                "screen_width": 0,
                "camera": False,
                "video_recording": False,
                "controller": False,
                "fullscreen": False,
                "topmost_window": False,
                "keep_aspect_ratio": False,
                # 键盘使用的状态标志
                "pause_keyboard": False,
                "disable_hotkey": False,
                "quick_paste": True,
                "hook_state": False,
                # 鼠标使用的状态标志
                "pause_mouse": False,
                "mouse_capture": False,
                "relative_mode": False,
                "hide_cursor": False,
                "correction_cursor": False,
                # 其他
                "block_input": False,
            }
        )

        # self.mutex = QMutex()
        # self.mutex_locker = QMutexLocker(self.mutex)
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

        # 加载键盘代码数据
        self.keyboard_code_data = KeyboardCodeData()

        # 加载配置文件
        self.config: MainConfig = MainConfig()
        self.load_config()

        # 子窗口
        self.about_dialog = AboutDialog()
        self.custom_key_dialog = CustomKeyDialog()
        self.indicator_lights_dialog = IndicatorLightsDialog()
        self.paste_board_dialog = PasteBoardDialog()
        self.settings_dialog = SettingsDialog()

        # 加载图标
        # 加载窗口图标
        self.init_window_icon()
        # 初始化菜单图标
        self.init_menu_icon()
        # 初始化子窗口图标
        self.init_sub_window_icon()

        # 初始化快捷键菜单
        self.init_shortcut_keys_menu()

        # 菜单初始状态设定
        self.init_menu_checked_state()

        # 初始化状态栏
        self.status_bar_manager = MainWindowStatusBarManager(self.statusbar)

        # 初始化 video widget
        self.video_widget: QVideoWidget | None = None
        self.video_disconnect_label = QLabel()
        self.init_video_widget()

        # 初始化 video session 相关变量
        self.video_session: VideoSession = VideoSession()

        # 初始化键盘以及鼠标数据的缓冲buffer
        self.keyboard_key_buffer: KeyboardKeyBuffer | None = None
        self.keyboard_indicator_buffer: KeyboardIndicatorBuffer | None = None
        self.mouse_buffer: MouseStateBuffer | None = None
        self.init_device_buffer()

        # 鼠标设置
        self.mouse_last_pos: None | QPoint = None
        self.mouse_relative_speed = self.config.mouse["relative_speed"]
        self.mouse_report_interval = 20
        self.mouse_report_at_next: bool = False
        mouse_report_timer = self.timer.create("MOUSE_REPORT_TIMER")
        mouse_report_timer.timeout.connect(self.mouse_report_timer_triggered)
        mouse_report_timer.start(self.mouse_report_interval)
        self.update_mouse_report_frequency()

        # 控制器消息处理线程
        self.controller_event: ControllerEventProxy = ControllerEventProxy()
        self.init_controller()
        controller_event_thread = self.threads.create("CONTROLLER_EVENT_THREAD")
        controller_event_thread.start()
        self.controller_event.moveToThread(controller_event_thread)
        # 每秒自动检查控制器连接
        controller_check_connection_timer = self.timer.create(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        controller_check_connection_timer.timeout.connect(
            self.check_controller_connection
        )
        controller_check_connection_timer.setInterval(1000)
        # controller_check_connection_timer.start()

        # 全屏模式设置
        self.fullscreen_event_command: str = "unknown"
        fullscreen_event_timer = self.timer.create("FULLSCREEN_EVENT_TIMER")
        fullscreen_event_timer.timeout.connect(
            self.execute_fullscreen_event_command
        )

        # 键盘钩子
        self.hook_manager = None
        self.hook_pressed_keys = []
        if platform.system() == "Windows":
            self.init_system_hook()

        # 绑定信号
        self.init_connect_signal()

        # Window accept mouse events
        self.setMouseTracking(True)

        # 显示操作系统警告
        self.tips_system_warning()

        # 启动自动连接
        self.auto_connect_on_startup()

    def load_icon(self, file_name: str) -> QIcon:
        search_path = [
            f"{self.source_directory}/icons/simple_style/{file_name}",
            f"{self.source_directory}/icons/{file_name}",
        ]
        file_path = None
        for path in search_path:
            if os.path.exists(path):
                file_path = path
                break
        assert file_path is not None
        return QIcon(file_path)

    def load_pixmap(self, file_name: str) -> QPixmap:
        search_path = [
            f"{self.source_directory}/icons/{file_name}",
            f"{self.source_directory}/icons/simple_style/{file_name}",
        ]
        file_path = None
        for path in search_path:
            if os.path.exists(path):
                file_path = path
                break
        assert file_path is not None
        return QPixmap(file_path)

    # 初始化窗口图标
    def init_window_icon(self) -> None:
        main_icon: QIcon = self.load_icon("main.ico")
        self.setWindowIcon(main_icon)

    # 初始化菜单栏图标
    def init_menu_icon(self) -> None:
        # menu_device_menu
        self.action_device_connect.setIcon(self.load_icon("connect.png"))
        self.action_device_disconnect.setIcon(self.load_icon("disconnect.png"))
        self.action_device_reload.setIcon(self.load_icon("reload.png"))
        self.action_device_reset.setIcon(self.load_icon("reset.png"))
        self.action_settings.setIcon(self.load_icon("setting.png"))
        self.action_minimize.setIcon(self.load_icon("window-minimize.png"))
        self.action_exit.setIcon(self.load_icon("window-close.png"))

        # menu_video
        self.action_fullscreen.setIcon(self.load_icon("fullscreen.png"))
        self.action_resize_window.setIcon(self.load_icon("resize.png"))
        self.action_topmost.setIcon(self.load_icon("topmost.png"))
        self.action_keep_aspect_ratio.setIcon(self.load_icon("ratio.png"))
        self.action_capture_image.setIcon(self.load_icon("capture.png"))
        self.action_record_video.setIcon(self.load_icon("record.png"))

        # menu_keyboard
        self.action_pause_keyboard.setIcon(self.load_icon("pause.png"))
        self.action_reload_keyboard.setIcon(self.load_icon("reload.png"))
        self.menu_shortcut_keys.setIcon(self.load_icon("keyboard-outline.png"))
        self.action_custom_key.setIcon(
            self.load_icon("keyboard-settings-outline.png")
        )
        self.action_disable_hotkey.setIcon(self.load_icon("hotkey.png"))
        self.action_paste_board.setIcon(self.load_icon("paste.png"))
        self.action_quick_paste.setIcon(self.load_icon("quick_paste.png"))
        self.action_system_hook.setIcon(self.load_icon("hook.png"))
        self.action_sync_indicator.setIcon(self.load_icon("sync.png"))
        self.action_indicator_light.setIcon(self.load_icon("capslock.png"))

        # menu_mouse
        self.action_pause_mouse.setIcon(self.load_icon("pause.png"))
        self.action_reload_mouse.setIcon(self.load_icon("reload.png"))
        self.action_capture_mouse.setIcon(self.load_icon("mouse.png"))
        self.action_release_mouse.setIcon(self.load_icon("mouse-off.png"))
        self.action_relative_mouse.setIcon(self.load_icon("relative.png"))
        self.action_hide_cursor.setIcon(self.load_icon("cursor.png"))
        self.action_correction_cursor.setIcon(
            self.load_icon("cursor-correction.png")
        )

        # menu_tools
        self.action_open_windows_device_manager.setIcon(
            self.load_icon("device.png")
        )
        self.action_open_on_screen_keyboard.setIcon(
            self.load_icon("keyboard-variant.png")
        )
        self.action_open_calculator.setIcon(self.load_icon("calculator.png"))
        self.action_open_snipping_tool.setIcon(
            self.load_icon("monitor-screenshot.png")
        )
        self.action_open_notepad.setIcon(self.load_icon("notebook-edit.png"))

        # menu_about
        self.action_about.setIcon(self.load_icon("python.png"))
        self.action_about_qt.setIcon(self.load_icon("qt.png"))
        self.action_debug_mode.setIcon(self.load_icon("debug.png"))

    # 初始化子窗口图标
    def init_sub_window_icon(self):
        self.about_dialog.setWindowIcon(self.load_icon("python.png"))
        self.custom_key_dialog.setWindowIcon(
            self.load_icon("keyboard-outline.png")
        )
        self.indicator_lights_dialog.setWindowIcon(
            self.load_icon("capslock.png")
        )
        self.paste_board_dialog.setWindowIcon(self.load_icon("paste.png"))
        self.settings_dialog.setWindowIcon(self.load_icon("setting.png"))

    # 初始化快捷键菜单
    def init_shortcut_keys_menu(self) -> None:
        self.menu_shortcut_keys.clear()
        for action_name in self.config.shortcut_keys.keys():
            action = self.menu_shortcut_keys.addAction(action_name)
            action.triggered.connect(
                lambda _checked, triggered_keys=action_name: self.shortcut_key_triggered(
                    triggered_keys
                )
            )
        pass

    # 初始化菜单点击状态
    def init_menu_checked_state(self):
        if self.config.video["keep_aspect_ratio"]:
            self.action_keep_aspect_ratio.setChecked(True)
            self.status.set_bool("keep_aspect_ratio", True)
        if self.config.ui["quick_paste"]:
            self.status.set_bool("quick_paste", True)
            self.action_quick_paste.setChecked(True)
        self.action_debug_mode.setChecked(project_var.debug_mode)

    # 初始化系统hook
    def init_system_hook(self):
        if platform.system() == "Windows":
            pass
        else:
            return
        self.hook_manager = pyHook.HookManager()
        self.hook_manager.KeyDown = self.hook_keyboard_down_event
        self.hook_manager.KeyUp = self.hook_keyboard_up_event
        pythoncom_timer = self.timer.create("PYTHONCOM_TIMER")
        pythoncom_timer.timeout.connect(lambda: pythoncom.PumpWaitingMessages())

    # 初始化菜单信号
    def init_menu_connect_signal(self):
        # device 菜单
        self.action_device_connect.triggered.connect(self.connect_devices)
        self.action_device_disconnect.triggered.connect(self.disconnect_devices)
        self.action_device_reload.triggered.connect(self.reload_devices)
        self.action_device_reset.triggered.connect(self.reset_devices)
        self.action_settings.triggered.connect(self.execute_settings_dialog)
        self.action_minimize.triggered.connect(self.showMinimized)
        self.action_exit.triggered.connect(self.close)

        # video 菜单
        self.action_fullscreen.triggered.connect(self.fullscreen_state_toggle)
        self.action_resize_window.triggered.connect(
            self.resize_window_with_video_resolution
        )
        self.action_topmost.triggered.connect(self.window_topmost_state_toggle)
        self.action_keep_aspect_ratio.triggered.connect(
            self.keep_aspect_ratio_toggle
        )
        self.action_capture_image.triggered.connect(
            self.image_capture_triggered
        )
        self.action_record_video.triggered.connect(self.video_record_triggered)

        # keyboard 菜单
        self.action_pause_keyboard.triggered.connect(
            self.sync_user_input_state_to_menu
        )
        self.action_reload_keyboard.triggered.connect(
            lambda: self.reload_controller("keyboard")
        )
        self.action_custom_key.triggered.connect(self.custom_key_dialog_show)
        self.custom_key_dialog.custom_key_send_signal.connect(
            self.custom_key_send
        )
        self.custom_key_dialog.custom_key_save_signal.connect(
            self.custom_key_save
        )
        self.action_disable_hotkey.triggered.connect(
            self.disable_hotkey_triggered
        )
        self.action_paste_board.triggered.connect(
            lambda: self.paste_board_dialog.exec()
        )
        self.paste_board_dialog.send_string_signal.connect(
            self.keyboard_send_string
        )
        self.action_quick_paste.triggered.connect(self.quick_paste_toggle)
        self.action_indicator_light.triggered.connect(
            self.execute_indicator_lights_dialog
        )
        self.action_system_hook.triggered.connect(self.system_hook_triggered)
        self.action_sync_indicator.triggered.connect(
            self.sync_indicator_triggered
        )
        # 键盘快捷键菜单设置
        self.init_shortcut_keys_menu()

        # mouse 菜单
        self.action_pause_mouse.triggered.connect(
            self.sync_user_input_state_to_menu
        )
        self.action_reload_mouse.triggered.connect(
            lambda: self.reload_controller("mouse")
        )
        self.action_capture_mouse.triggered.connect(
            self.mouse_capture_triggered
        )
        self.action_release_mouse.triggered.connect(
            self.mouse_capture_release_triggered
        )
        self.action_relative_mouse.triggered.connect(
            self.mouse_relative_mode_triggered
        )
        self.action_hide_cursor.triggered.connect(
            self.mouse_hide_cursor_triggered
        )
        self.action_correction_cursor.triggered.connect(
            self.mouse_cursor_correction_triggered
        )

        # tools 菜单
        self.action_open_windows_device_manager.triggered.connect(
            lambda: self.menu_tools_actions("devmgmt.msc")
        )
        self.action_open_on_screen_keyboard.triggered.connect(
            lambda: self.menu_tools_actions("osk")
        )
        self.action_open_calculator.triggered.connect(
            lambda: self.menu_tools_actions("calc")
        )
        self.action_open_snipping_tool.triggered.connect(
            lambda: self.menu_tools_actions("snipping_tool")
        )
        self.action_open_notepad.triggered.connect(
            lambda: self.menu_tools_actions("notepad")
        )

        # about
        self.action_about.triggered.connect(lambda: self.about_dialog.exec())
        self.action_about_qt.triggered.connect(lambda: QApplication.aboutQt())
        self.action_debug_mode.triggered.connect(self.switch_debug_mode)

    # 初始化信号槽连接
    def init_connect_signal(self) -> None:
        self.init_menu_connect_signal()

        # keyboard 菜单需要的信号连接
        self.indicator_lights_dialog.lock_key_clicked_signal.connect(
            self.update_keyboard_indicator_buffer_with_hid_code
        )

        # controller event
        self.controller_event.command_reply_signal.connect(
            self.controller_command_reply
        )
        pass

    def load_config(self) -> None:
        try:
            self.config = MainConfig(
                project_binary_directory_path("config.yaml")
            )
            config_version = self.config.root["config_version"]
            if config_version != CONFIG_VERSION_STRING:
                raise ValueError(
                    self.tr(
                        "The configuration file does not match the program.\n"
                    )
                    + self.tr(
                        "Please delete the existing configuration file.\n"
                    )
                )
        except Exception as err:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Import config error:\n{}\n").format(err),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.NoButton,
            )
            sys.exit(1)

    def save_config(self) -> None:
        # 保存配置文件
        self.config.save_to_file()

    def to_enabled_string(self, value: bool) -> str:
        if value:
            return self.tr("Enable")
        else:
            return self.tr("Disable")

    # 固定延迟
    @staticmethod
    def sleep_ms(interval: int = 1):
        QThread.msleep(interval)

    # 随机延迟
    @staticmethod
    def random_sleep_ms(min_interval: int = 0, max_interval: int = 100):
        random_time = int(random.uniform(min_interval, max_interval))
        QThread.msleep(random_time)

    ######################################################################
    # 主窗口相关函数
    ######################################################################
    # 连接设备
    def connect_devices(self):
        self.connect_video_device()
        self.connect_controller()

    # 断开设备
    def disconnect_devices(self):
        self.disconnect_video_device()
        self.disconnect_controller()

    # 重载设备
    def reload_devices(self):
        self.reload_controller("all")

    # 重置设备
    def reset_devices(self):
        self.reset_controller()

    # 启动后自动连接
    def auto_connect_on_startup(self):
        if self.config.connection["auto_connect"]:
            self.connect_devices()

    # 全屏状态切换
    def fullscreen_state_toggle(self) -> None:
        self.status.reverse_bool("fullscreen")
        if self.status.is_enabled("fullscreen"):
            if self.config.ui["tips_fullscreen"]:
                _, close_next_tip = MessageBox.optional_information(
                    self,
                    self.tr("Tip"),
                    self.tr("Press Ctrl+Alt+F11 to toggle fullscreen.\n")
                    + self.tr(
                        "Or stay cursor at left top corner to show menu bar."
                    ),
                    self.tr("Don't show again."),
                    False,
                    QMessageBox.StandardButton.Ok,
                    QMessageBox.StandardButton.NoButton,
                )
                if (
                    close_next_tip is True
                    and self.config.ui["tips_fullscreen"] is True
                ):
                    self.config.ui["tips_fullscreen"] = False
                    self.save_config()
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
            self.action_resize_window.setEnabled(False)
            self.statusBar().hide()
            self.menuBar().hide()
        else:
            event_timer = self.timer.get("FULLSCREEN_EVENT_TIMER")
            event_timer.stop()
            self.showNormal()
            self.action_fullscreen.setChecked(False)
            self.action_resize_window.setEnabled(True)
            self.statusBar().show()
            self.menuBar().show()

    # 执行全屏时事件命令
    def execute_fullscreen_event_command(self):
        event_timer = self.timer.get("FULLSCREEN_EVENT_TIMER")
        command = self.fullscreen_event_command
        if command == "show_menu_bar":
            if self.menuBar().isHidden():
                self.menuBar().show()
        elif command == "show_status_bar":
            if self.statusBar().isHidden():
                self.statusBar().show()
        elif command == "hide_all":
            if not self.menuBar().isHidden():
                self.menuBar().hide()
            if not self.statusBar().isHidden():
                self.statusBar().hide()
        else:
            pass
        event_timer.stop()

    # 切换保持窗口在最前
    def window_topmost_state_toggle(self):
        self.status.reverse_bool("topmost_window")
        current_window_flag = self.windowFlags()
        if self.status.is_enabled("topmost_window"):
            self.windowHandle().setFlags(
                current_window_flag
                | Qt.WindowStaysOnTopHint
                | Qt.WindowCloseButtonHint
            )
        else:
            self.windowHandle().setFlags(
                current_window_flag & ~Qt.WindowStaysOnTopHint
                | Qt.WindowCloseButtonHint
            )
        self.status_bar_manager.show_message(
            self.tr("Window topmost: ")
            + self.to_enabled_string(self.status.is_enabled("topmost_window"))
        )
        self.action_topmost.setChecked(self.status.is_enabled("topmost_window"))

    # 保持比例拉伸
    def keep_aspect_ratio_toggle(self):
        self.status.reverse_bool("keep_aspect_ratio")
        if self.status.is_enabled("keep_aspect_ratio"):
            self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
            self.action_keep_aspect_ratio.setChecked(True)
        else:
            self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)
            self.action_keep_aspect_ratio.setChecked(False)
        self.status_bar_manager.show_message(
            self.tr("Keep aspect ratio: ")
            + self.to_enabled_string(self.status["keep_aspect_ratio"])
        )

    # 视频帧捕捉完成
    def image_capture_done(self, capture_id: int, preview: QImage) -> None:
        logger.debug("image_capture_id: ", capture_id)
        file_name = QFileDialog.getSaveFileName(
            self,
            self.tr("Image Save"),
            "untitled.png",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )[0]
        if file_name == "":
            return
        preview.save(file_name)
        self.status_bar_manager.show_message(
            self.tr("Image saved to") + f" {file_name}"
        )

    # 保存当前帧命令触发
    def image_capture_triggered(self) -> None:
        self.video_session.image_capture.imageCaptured.disconnect(
            self.image_capture_done
        )
        self.video_session.image_capture.imageCaptured.connect(
            self.image_capture_done
        )
        if self.status.is_enabled("camera"):
            self.video_session.image_capture.capture()

    def video_record_triggered(self) -> None:
        record: QMediaRecorder = self.video_session.video_record
        if not self.status.is_enabled("camera"):
            return

        if self.status.is_enabled("video_recording"):
            record.stop()
            self.status.set_bool("video_recording", False)
            self.action_record_video.setText(self.tr("Record video"))
            self.action_record_video.setChecked(False)
            self.status_bar_manager.show_message(
                self.tr("Video recording stopped")
            )
        else:
            file_name = QFileDialog.getSaveFileName(
                self,
                self.tr("Video save"),
                "output.mp4",
                "Video (*.mp4)",
            )[0]
            if file_name == "":
                return
            if (
                self.video_session.video_record.recorderState()
                != QMediaRecorder.RecorderState.StoppedState
            ):
                record.stop()
            record.setOutputLocation(QUrl.fromLocalFile(file_name))
            record.record()
            self.status.set_bool("video_recording", True)
            self.action_record_video.setText(self.tr("Stop recording"))
            self.action_record_video.setChecked(True)
            self.status_bar_manager.show_message(
                self.tr("Video recording started")
            )

    # 同步用户输入状态到菜单
    def sync_user_input_state_to_menu(self):
        if self.action_pause_keyboard.isChecked() is True:
            self.status.set_bool("pause_keyboard", True)
        else:
            self.status.set_bool("pause_keyboard", False)

        if self.action_pause_mouse.isChecked() is True:
            self.status.set_bool("pause_mouse", True)
        else:
            self.status.set_bool("pause_mouse", False)

    # 快捷键发送
    def shortcut_key_send(self, keys: list[str]):
        key_code_list = list()
        for key_name in keys:
            status, key_code = (
                self.keyboard_code_data.convert_key_name_to_hid_code(key_name)
            )
            if not status:
                continue
            key_code_list.append(key_code)
        for key_code in key_code_list:
            self.update_keyboard_buffer_with_hid_code(
                key_code, KeyStateEnum.PRESS
            )
            self.send_keyboard_buffer()
        self.random_sleep_ms()
        for key_code in key_code_list:
            self.update_keyboard_buffer_with_hid_code(
                key_code, KeyStateEnum.RELEASE
            )
            self.send_keyboard_buffer()

    # 快捷键触发
    def shortcut_key_trigger(self, action_name: str):
        for keys_name in self.config.shortcut_keys:
            if action_name == keys_name:
                send_buffer = self.config.shortcut_keys[action_name]
                self.shortcut_key_send(send_buffer)
                break
            pass
        pass

    def custom_key_dialog_show(self):
        self.custom_key_dialog.exec()

    def custom_key_send(self, keys: list[str]):
        self.shortcut_key_send(keys)

    def custom_key_save(self, name: str, keys: list[str]):
        custom_key_data = {name: keys}
        self.config.shortcut_keys.update(custom_key_data)
        self.save_config()
        self.init_shortcut_keys()

    # 快捷键菜单触发
    def shortcut_key_triggered(self, action_name: str):
        for keys_name in self.config.shortcut_keys:
            if action_name == keys_name:
                send_buffer = self.config.shortcut_keys[action_name]
                self.shortcut_key_send(send_buffer)
                break
            pass
        pass

    # 禁用热键菜单触发
    def disable_hotkey_triggered(self):
        hotkey_status = self.action_disable_hotkey.isChecked()
        self.status.set_bool("disable_hotkey", hotkey_status)

    # 屏蔽或者恢复用户输入
    def user_input_block(self, block: bool):
        self.status.set_bool("block_input", block)

    # 使用键盘发送字符串
    def keyboard_send_string(self, data: str):
        self.user_input_block(True)
        status, shift_hid_code = (
            self.keyboard_code_data.convert_key_name_to_hid_code("shift")
        )
        assert status is not False
        # 强制关闭 capslock
        if self.keyboard_indicator_buffer.caps_lock:
            self.update_keyboard_indicator_buffer("caps_lock")

        # 强制清空缓冲区
        self.clear_keyboard_buffer()
        self.send_keyboard_buffer()

        for character in data:
            if not character.isascii():
                logger.critical(f"Character not supported: {character}")
                continue
            shift_flag = False
            # 如果是需要shift的符号
            if character in SHIFT_SYMBOL:
                shift_flag = True
            # 如果是大写字母
            if character.isupper():
                shift_flag = True
            status, key_code = (
                self.keyboard_code_data.convert_key_name_to_hid_code(character)
            )

            if not status:
                logger.critical(f"character key code not found: {character}")
                continue
            if shift_flag:
                self.update_keyboard_buffer_with_hid_code(
                    shift_hid_code, KeyStateEnum.PRESS
                )
                self.send_keyboard_buffer()

                self.update_keyboard_buffer_with_hid_code(
                    key_code, KeyStateEnum.PRESS
                )
                self.send_keyboard_buffer()

                self.update_keyboard_buffer_with_hid_code(
                    key_code, KeyStateEnum.RELEASE
                )
                self.send_keyboard_buffer()

                self.update_keyboard_buffer_with_hid_code(
                    shift_hid_code, KeyStateEnum.RELEASE
                )
                self.send_keyboard_buffer()
            else:
                self.update_keyboard_buffer_with_hid_code(
                    key_code, KeyStateEnum.PRESS
                )
                self.send_keyboard_buffer()

                self.update_keyboard_buffer_with_hid_code(
                    key_code, KeyStateEnum.RELEASE
                )
                self.send_keyboard_buffer()
            self.sleep_ms(self.config.paste_board["interval"])
        self.user_input_block(False)

    # 快速粘贴功能开关切换
    def quick_paste_toggle(self):
        self.status.reverse_bool("quick_paste")
        quick_paste = self.status.get_bool("quick_paste")
        self.action_quick_paste.setChecked(quick_paste)
        self.status_bar_manager.show_message(
            self.tr("Quick paste: ") + self.to_enabled_string(quick_paste)
        )

    # 快速粘贴功能触发
    def quick_paste_trigger(self):
        # 获取剪贴板内容
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if len(text) == 0:
            self.status_bar_manager.show_message(self.tr("Clipboard is empty"))
            return
        self.status_bar_manager.show_message(
            self.tr("Quick pasting") + f" {len(text)} " + self.tr("characters")
        )
        self.clear_keyboard_buffer()
        self.send_keyboard_buffer()

        self.keyboard_send_string(text)

    # 发送请求同步键盘指示灯状态
    def sync_indicator_triggered(self):
        self.sync_keyboard_indicator_to_buffer()

    # 同步键盘指示器缓冲区
    def sync_keyboard_indicator_to_buffer(self):
        self.keyboard_indicator_buffer.clear()
        self.controller_command_send("keyboard_read", None)

    def execute_indicator_lights_dialog(self):
        if self.indicator_lights_dialog.isVisible():
            self.indicator_lights_dialog.activateWindow()
            return
        self.move_dialog_to_center(self.indicator_lights_dialog)
        self.indicator_lights_dialog.update_buffer(
            self.keyboard_indicator_buffer
        )
        self.indicator_lights_dialog.refresh_status_from_buffer()
        self.indicator_lights_dialog.exec()

    # 系统钩子
    def system_hook_triggered(self):
        system_name = platform.system()
        if system_name == "Windows":
            pass
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("System hook only support windows."),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.NoButton,
            )
            return
        pythoncom_timer = self.timer.get("PYTHONCOM_TIMER")
        self.status.reverse_bool("hook_state")
        hook_state = self.status.get_bool("hook_state")
        self.action_system_hook.setChecked(hook_state)
        self.status_bar_manager.show_message(
            self.tr("System hook: ") + self.to_enabled_string(hook_state)
        )
        if hook_state:
            pythoncom_timer.start(5)
            self.hook_manager.HookKeyboard()
        else:
            self.hook_manager.UnhookKeyboard()
            pythoncom_timer.stop()

    # 捕获鼠标功能
    def mouse_capture_triggered(self) -> None:
        self.status.set_bool("mouse_capture", True)
        self.status_bar_manager.show_message(
            self.tr("Mouse capture on (Press Ctrl+Alt+F12 to release)")
        )

    # 释放鼠标功能
    def mouse_capture_release_triggered(self) -> None:
        self.status.set_bool("mouse_capture", False)

    # 相对模式菜单触发
    def mouse_relative_mode_triggered(self):
        self.status.reverse_bool("relative_mode")
        relative_mode = self.status.get_bool("relative_mode")
        self.action_relative_mouse.setChecked(relative_mode)
        self.status_bar_manager.show_message(
            self.tr("Relative mouse: ") + self.to_enabled_string(relative_mode)
        )

    # 隐藏指针
    def mouse_hide_cursor_triggered(self) -> None:
        self.status.reverse_bool("hide_cursor")
        hide_cursor = self.status.get_bool("hide_cursor")
        self.action_hide_cursor.setChecked(hide_cursor)
        self.status_bar_manager.show_message(
            self.tr("Hide cursor when capture mouse: ")
            + self.to_enabled_string(hide_cursor)
        )

    # 光标校正
    def mouse_cursor_correction_triggered(self) -> None:
        self.status.reverse_bool("correction_cursor")
        correction_cursor = self.status.get_bool("correction_cursor")
        self.action_correction_cursor.setChecked(correction_cursor)
        self.status_bar_manager.show_message(
            self.tr("Correction cursor: ")
            + self.to_enabled_string(correction_cursor)
        )

    # 工具菜单执行系统工具
    def menu_tools_actions(self, action_name: str):
        system_name = platform.system().lower()
        if system_name == "windows":  # sys.platform == "win32":
            pass
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("This tool only support windows"),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.NoButton,
            )
            return
        file_path: str | None = None
        if action_name == "devmgmt.msc":
            mmc_path = shutil.which("mmc.exe")
            msc_path = shutil.which("devmgmt.msc")
            file_path = f"{mmc_path} {msc_path}"
        elif action_name == "osk":
            file_path = shutil.which("osk.exe")
        elif action_name == "calc":
            file_path = shutil.which("calc.exe")
        elif action_name == "snipping_tool":
            file_path = shutil.which("SnippingTool.exe")
        elif action_name == "notepad":
            file_path = shutil.which("notepad.exe")
        else:
            pass
        if file_path is not None:
            subprocess.run(file_path)

    # 非 windows 警告
    def tips_system_warning(self):
        system_name = platform.system().lower()
        if system_name == "windows":
            return
        if self.config.ui["tips_system_warning"] is False:
            return
        _, close_next_tip = MessageBox.optional_information(
            self,
            self.tr("Tip"),
            self.tr("The current operating system is not Windows.\n")
            + self.tr("Some features will be unavailable.\n"),
            self.tr("Don't show again."),
            False,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.NoButton,
        )
        if (
            close_next_tip is True
            and self.config.ui["tips_system_warning"] is True
        ):
            self.config.ui["tips_system_warning"] = False
            self.save_config()

    # 打开debug模式
    def switch_debug_mode(self):
        project_var.debug_mode = not project_var.debug_mode
        self.action_debug_mode.setChecked(project_var.debug_mode)
        logger_init()

    ######################################################################
    # 控制器相关函数
    ######################################################################
    # 初始化控制器
    def init_controller(self):
        device_config: dict = copy.copy(self.config.controller)
        device_config["controller_type"] = self.config.controller["type"]
        device_config["resolution_x"] = self.config.video["resolution_x"]
        device_config["resolution_y"] = self.config.video["resolution_y"]
        device_config["relative_click"] = self.config.mouse["relative_click"]

        self.controller_event.device_init(device_config)

    # 连接控制器
    def connect_controller(self):
        self.init_controller()
        self.controller_command_send("device_open", None)
        self.reload_controller("all")
        self.controller_command_send("keyboard_read", None)
        self.mouse_capture_triggered()
        check_connection_timer = self.timer.get(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        check_connection_timer.start()

    # 断开控制器
    def disconnect_controller(self):
        check_connection_timer = self.timer.get(
            "CONTROLLER_CHECK_CONNECTION_TIMER"
        )
        check_connection_timer.stop()
        self.controller_command_send("device_close", None)

    # 重载控制器
    def reload_controller(self, cmd: str):
        # cmd = ["mouse", "keyboard", "all", "any"]
        if cmd == "mouse":
            self.clear_mouse_buffer()
        elif cmd == "keyboard":
            self.clear_keyboard_buffer()
        else:
            self.clear_mouse_buffer()
            self.clear_keyboard_buffer()
        self.controller_command_send("device_reload", cmd)

    # 重置控制器
    def reset_controller(self):
        self.controller_command_send("device_reset", None)

    # 检查控制器连接
    def check_controller_connection(self):
        if self.status.is_enabled("controller"):
            self.controller_command_send("check_connection", None)

    # 控制器发送命令信号
    def controller_command_send(self, command: str, data: typing.Any):
        self.controller_event.command_send_signal.emit(command, data)

    # 接收控制器回复
    def controller_command_reply(
        self, command: str, status: int, data: typing.Any
    ):
        ignored_command = [
            "device_reload",
            "device_reset",
            "mouse_relative_write",
            "mouse_absolute_write",
            "keyboard_write",
        ]
        if command == "device_open":
            if status == 0:
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
        elif command == "check_connection":
            if status != 0:
                # 检查连接返回失败
                self.disconnect_controller()
                self.connect_controller()
        elif command == "keyboard_read":
            if status == 0:
                logger.debug("keyboard indicator read succeed")
                self.keyboard_indicator_buffer.from_dict(data)
                self.status_bar_manager.update_label_status(
                    self.keyboard_key_buffer, self.keyboard_indicator_buffer
                )
            else:
                logger.debug("keyboard indicator read failed")
        elif command in ignored_command:
            pass
        else:
            logger.debug(f"Unhandled command reply: {command}")
            pass

    ######################################################################
    # 键盘鼠标缓冲区相关函数
    ######################################################################

    @staticmethod
    def convert_to_button_code(value: Qt.MouseButton) -> MouseButtonCodeEnum:
        convert_table: dict[Qt.MouseButton, MouseButtonCodeEnum] = {
            Qt.LeftButton: MouseButtonCodeEnum.LEFT_BUTTON,
            Qt.RightButton: MouseButtonCodeEnum.RIGHT_BUTTON,
            Qt.MiddleButton: MouseButtonCodeEnum.MIDDLE_BUTTON,
            Qt.XButton1: MouseButtonCodeEnum.XBUTTON1_BUTTON,
            Qt.XButton2: MouseButtonCodeEnum.XBUTTON2_BUTTON,
        }
        button_code = convert_table.get(
            value, MouseButtonCodeEnum.UNKNOWN_BUTTON
        )
        return button_code

    def init_device_buffer(self):
        # 初始化键盘以及鼠标数据的缓冲buffer
        self.keyboard_key_buffer: KeyboardKeyBuffer = KeyboardKeyBuffer()
        self.keyboard_indicator_buffer: KeyboardIndicatorBuffer = (
            KeyboardIndicatorBuffer()
        )
        self.mouse_buffer = MouseStateBuffer()

    # 发送键盘缓冲区到控制器
    def send_keyboard_buffer(self):
        if project_var.debug_mode:
            logger.debug(f"keyboard send: {str(self.keyboard_key_buffer)}")
        self.controller_command_send(
            "keyboard_write", self.keyboard_key_buffer.dup()
        )
        self.status_bar_manager.update_label_status(
            self.keyboard_key_buffer, self.keyboard_indicator_buffer
        )

    # 清空键盘按键缓冲区
    def clear_keyboard_buffer(self):
        self.keyboard_key_buffer.clear()
        self.controller_command_send(
            "keyboard_write", self.keyboard_key_buffer.dup()
        )

    # 清空鼠标缓冲区
    def clear_mouse_buffer(self):
        self.mouse_buffer.clear()

    # 更新键盘缓冲区(hid_code)
    def update_keyboard_buffer_with_hid_code(
        self, hid_code: int, state: KeyStateEnum
    ) -> None:
        if state == KeyStateEnum.PRESS:
            self.keyboard_key_buffer.key_press(hid_code)
        else:
            self.keyboard_key_buffer.key_release(hid_code)

    # 更新键盘缓冲区(scancode)
    def update_keyboard_buffer_with_scancode(
        self, scancode: int, state: KeyStateEnum
    ) -> None:
        status, hid_code = (
            self.keyboard_code_data.convert_scan_code_to_hid_code(scancode)
        )
        if not status:
            return
        self.update_keyboard_buffer_with_hid_code(hid_code, state)

    # 更新键盘缓冲区(qt key value)
    def update_keyboard_buffer_with_qt_key_value(
        self, key_value: int, state: KeyStateEnum
    ) -> None:
        status, hid_code = (
            self.keyboard_code_data.convert_qt_key_value_to_hid_code(key_value)
        )
        if not status:
            return
        self.update_keyboard_buffer_with_hid_code(hid_code, state)

    # 更新键盘缓冲区 默认(hid_code)
    def update_keyboard_buffer(
        self, hid_code: int, state: KeyStateEnum
    ) -> None:
        self.update_keyboard_buffer_with_hid_code(hid_code, state)

    # 使用hid code更新键盘状态键缓冲区
    def update_keyboard_indicator_buffer_with_hid_code(
        self, hid_code: int
    ) -> None:
        _, caps_lock = self.keyboard_code_data.convert_key_name_to_hid_code(
            "caps_lock"
        )
        _, scroll_lock = self.keyboard_code_data.convert_key_name_to_hid_code(
            "scroll_lock"
        )
        _, num_lock = self.keyboard_code_data.convert_key_name_to_hid_code(
            "num_lock"
        )

        if hid_code == caps_lock:
            self.keyboard_indicator_buffer.caps_lock = (
                not self.keyboard_indicator_buffer.caps_lock
            )
        elif hid_code == num_lock:
            self.keyboard_indicator_buffer.num_lock = (
                not self.keyboard_indicator_buffer.num_lock
            )
        elif hid_code == scroll_lock:
            self.keyboard_indicator_buffer.scroll_lock = (
                not self.keyboard_indicator_buffer.scroll_lock
            )
        else:
            pass

    # 更新鼠标坐标缓冲区(绝对坐标模式)
    def update_mouse_position_buffer_with_absolute_mode(self, x: int, y: int):
        self.mouse_last_pos = None
        if not self.status.is_enabled("camera"):
            x_res = self.video_disconnect_label.width()
            y_res = self.video_disconnect_label.height()
            width = self.video_disconnect_label.width()
            height = self.video_disconnect_label.height()
            x_pos = self.video_disconnect_label.pos().x()
            y_pos = self.video_disconnect_label.pos().y()
        else:
            x_res = self.config.video["resolution_x"]
            y_res = self.config.video["resolution_y"]
            width = self.video_widget.width()
            height = self.video_widget.height()
            x_pos = self.video_widget.pos().x()
            y_pos = self.video_widget.pos().y()
        x_diff = 0
        y_diff = 0
        if self.config.video["keep_aspect_ratio"]:
            cam_scale = y_res / x_res
            finder_scale = height / width
            if finder_scale > cam_scale:
                x_diff = 0
                y_diff = height - width * cam_scale
            elif finder_scale < cam_scale:
                x_diff = width - height / cam_scale
                y_diff = 0
        # 启用游标偏移校正
        if self.status.is_enabled("correction_cursor"):
            x_pos += self.config.mouse["cursor_offset_x"]
            y_pos += self.config.mouse["cursor_offset_y"]
        x_hid = (x - x_diff / 2 - x_pos) / (width - x_diff)
        y_hid = (y - y_diff / 2 - y_pos) / (height - y_diff)
        x_hid = max(min(x_hid, 1), 0)
        y_hid = max(min(y_hid, 1), 0)
        self.mouse_buffer.set_point(x_hid, y_hid)
        """
        self.status_bar_manager.show_message(
            f"X={x_hid * x_res:.0f}, Y={y_hid * y_res:.0f}"
        )
        """
        self.status_bar_manager.show_message(
            f"X={x_hid * x_res:.0f}, Y={y_hid * y_res:.0f}"
        )
        # logger.debug(f"X={x_hid * x_res:.0f}, Y={y_hid * y_res:.0f}")

    # 更新鼠标坐标缓冲区(相对坐标模式)
    def update_mouse_position_buffer_with_relative_mode(self):
        relative_mouse_speed = self.config.mouse["relative_speed"]
        middle_pos = self.mapToGlobal(
            QPoint(int(self.width() / 2), int(self.height() / 2))
        )
        mouse_pos = QCursor.pos()
        if self.mouse_last_pos is not None:
            rel_x, rel_y = self.mouse_buffer.get_point()
            rel_x += (
                mouse_pos.x() - self.mouse_last_pos.x()
            ) * relative_mouse_speed
            rel_y += (
                mouse_pos.y() - self.mouse_last_pos.y()
            ) * relative_mouse_speed
            self.mouse_last_pos = mouse_pos
            self.mouse_buffer.set_point(rel_x, rel_y)
            # logger.debug(f"relative mode X={rel_x}, Y={rel_y}")
            if self.status.is_enabled("disable_hotkey"):
                # 为了保证用户可以退出相对坐标模式，程序自身热键将强制启用
                self.action_disable_hotkey.setChecked(False)
                self.disable_hotkey_triggered()
            self.status_bar_manager.show_message(
                self.tr("Press Ctrl+Alt+F12 to release mouse")
            )
            if (
                abs(mouse_pos.x() - middle_pos.x()) > 25
                or abs(mouse_pos.y() - middle_pos.y()) > 25
            ):
                QCursor.setPos(middle_pos)
                self.mouse_last_pos = middle_pos
        else:
            self.mouse_buffer.clear_point()
            QCursor.setPos(middle_pos)
            self.mouse_last_pos = middle_pos

    # 更新鼠标坐标缓冲区
    def update_mouse_position_buffer(self, x: int, y: int):
        if not self.status.is_enabled("relative_mode"):
            self.update_mouse_position_buffer_with_absolute_mode(x, y)
        else:
            self.update_mouse_position_buffer_with_relative_mode()
        self.mouse_report_at_next = True

    ######################################################################
    # 鼠标相关函数
    ######################################################################

    # 更新鼠标更新频率
    def update_mouse_report_frequency(self, frame_rate: int = 60):
        if self.config.mouse["report_frequency"] != 0:
            self.mouse_report_interval = (
                1000 / self.config.mouse["report_frequency"]
            )
        else:
            self.mouse_report_interval = 1000 / frame_rate
        mouse_report_timer = self.timer.get("MOUSE_REPORT_TIMER")
        assert mouse_report_timer is not None
        if mouse_report_timer is not None:
            mouse_report_timer.setInterval(self.mouse_report_interval)

    # 滚轮事件
    def mouse_report_scroll(self):
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.controller_command_send(command, self.mouse_buffer.dup())
        self.mouse_buffer.wheel = MouseWheelStateEnum.STOP

    # 鼠标报告定时器触发
    # 此函数会向控制器发送鼠标指令
    def mouse_report_timer_triggered(self):
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        if self.mouse_report_at_next:
            self.controller_command_send(command, self.mouse_buffer.dup())
            if self.status.is_enabled("relative_mode"):
                self.mouse_buffer.clear_point()
        self.mouse_report_at_next = False

    ######################################################################
    # video widget相关函数
    ######################################################################

    # 初始化 video widget
    def init_video_widget(self) -> None:
        self.video_widget = QVideoWidget()
        self.video_widget.setAttribute(Qt.WA_OpaquePaintEvent)
        self.takeCentralWidget()
        self.setCentralWidget(self.video_widget)
        self.video_widget.setMouseTracking(True)
        self.video_widget.children()[0].setMouseTracking(True)
        self.video_widget.hide()

        s_format = QSurfaceFormat.defaultFormat()
        s_format.setSwapInterval(0)
        QSurfaceFormat.setDefaultFormat(s_format)

        self.video_disconnect_label = QLabel()
        image_pixmap = self.load_pixmap("screen.svg")
        """
        image_pixmap = image_pixmap.scaled(
            128,
            128,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        """
        self.video_disconnect_label.setPixmap(image_pixmap)
        self.video_disconnect_label.setAlignment(Qt.AlignCenter)
        self.video_disconnect_label.setMouseTracking(True)
        self.takeCentralWidget()
        self.setCentralWidget(self.video_disconnect_label)
        self.video_disconnect_label.show()

    # 设置 video_widget 是否启用
    def set_video_widget_enable(self, enable: bool):
        if enable:
            self.video_disconnect_label.hide()
            self.video_widget.show()
            self.takeCentralWidget()
            self.setCentralWidget(self.video_widget)
        else:
            self.video_widget.hide()
            self.video_disconnect_label.show()
            self.takeCentralWidget()
            self.setCentralWidget(self.video_disconnect_label)

    # frame 改变
    def video_widget_frame_changed(self, frame: QVideoFrame) -> None:
        self.video_widget.isWindow()
        video_slink = self.video_widget.videoSink()
        video_slink.setVideoFrame(frame)
        self.video_widget.update()
        self.video_widget.repaint()

    # 判断屏幕大小是否足够
    @staticmethod
    def is_screen_size_sufficient(
        required_height: int,
        required_width: int,
        screen_height: int,
        screen_width: int,
    ) -> bool:
        if not screen_height >= required_height:
            return False
        if not screen_width >= required_width:
            return False
        return True

    # 移动窗口到中心
    def move_window_to_center(self) -> None:
        qr = self.frameGeometry()
        # 获取中心点
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        # 移动中心点到获取的中心点
        qr.moveCenter(cp)
        # 根据中心点重新计算左上角的坐标
        point = qr.topLeft()
        self.move(point)

    # 通过视频设备分辨率调整窗口大小
    def resize_window_with_video_resolution(self) -> None:
        if self.status.is_enabled("fullscreen"):
            return
        menu_bar_height = self.menubar.height()
        status_bar_height = self.statusbar.height()
        # 菜单和状态栏附带高度
        additional_height = menu_bar_height + status_bar_height
        # 附带宽度
        additional_width = 0

        # 窗口推荐大小
        recommend_height = self.config.video["resolution_y"] + additional_height
        recommend_width = self.config.video["resolution_x"] + additional_width

        screen_available_size = (
            QGuiApplication.primaryScreen().availableGeometry()
        )
        screen_available_height = screen_available_size.height()
        screen_available_width = screen_available_size.width()
        if self.is_screen_size_sufficient(
            recommend_height,
            recommend_width,
            screen_available_height,
            screen_available_width,
        ):
            # 如果屏幕大小足够
            self.showNormal()
            self.resize(
                recommend_width,
                recommend_height,
            )
        else:
            # 如屏幕大小不够则按比例缩小尺寸
            while not (
                self.is_screen_size_sufficient(
                    recommend_height,
                    recommend_width,
                    screen_available_height,
                    screen_available_width,
                )
            ):
                recommend_height = int(recommend_height * 1 / 2)
                recommend_width = int(recommend_width * 1 / 2)
            self.showNormal()
            self.resize(
                recommend_width,
                recommend_height,
            )

        # 如果自动居中打开则自动居中窗口
        if self.config.ui["window_auto_to_center"]:
            self.move_window_to_center()
        # 如果自动最大化选项打开则自动最大化窗口
        if self.config.ui["window_auto_maximized"]:
            self.showMaximized()
        # 保持视频比例
        if self.config.video["keep_aspect_ratio"]:
            self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        else:
            self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)

    ######################################################################
    # 视频设备相关函数
    ######################################################################

    # 摄像头错误发生时处理的槽函数
    def video_device_error_occurred(
        self, error: QCamera.Error, message: str
    ) -> None:
        error_s = (
            f"Device: {self.video_device.description()}\n"
            f"Error code: {error}\n"
            f"Message: {message}\n"
        )
        self.disconnect_video_device()
        QMessageBox.critical(
            self,
            self.tr("Video Device Error"),
            error_s,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.NoButton,
        )

    # 视频设备初始化
    def init_video_device(self) -> bool:
        status: bool = False
        try:
            # 使用配置初始化设备
            self.video_session.init_video_device_with_config(self.config.video)
            self.video_session.init_capture_session_with_config(
                self.config.video_record
            )

            camera = self.video_session.camera
            video_sink = self.video_session.video_sink
            # 注册信号
            video_sink.videoFrameChanged.connect(
                self.video_widget_frame_changed
            )
            camera.errorOccurred.connect(self.video_device_error_occurred)
            camera.start()

            if not camera.isActive():
                self.status.set_bool("camera", False)
                raise RuntimeError(self.tr("Video device start failed"))
            else:
                self.status.set_bool("camera", True)
            self.status.set_bool("video_recording", False)
            status = True
        except RuntimeError as error:
            error_message = str(error)
            QMessageBox.critical(
                self,
                self.tr("Video initialization error"),
                error_message,
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.NoButton,
            )
        return status

    # 启用视频设备
    def connect_video_device(self) -> None:
        if not self.init_video_device():
            return
        if not self.status.is_enabled("fullscreen"):
            self.resize_window_with_video_resolution()
        fps = self.video_session.camera.cameraFormat().maxFrameRate()
        self.set_video_widget_enable(True)
        self.setWindowTitle(
            f"{self.WINDOW_TITLE}"
            + " - "
            + f"{self.config.video["resolution_x"]}x{self.config.video["resolution_y"]}"
            + " @ "
            + f"{fps:.1f}"
        )
        self.update_mouse_report_frequency(int(fps))

    # 断开视频设备
    def disconnect_video_device(self) -> None:
        if self.status.is_enabled("camera"):
            self.video_session.camera.stop()
            self.video_session.camera.setActive(False)
            self.status.set_bool("camera", False)
        self.set_video_widget_enable(False)
        self.setWindowTitle(self.WINDOW_TITLE)

    ######################################################################
    # Hook
    ######################################################################
    # pyhook scan code 转换表
    SCAN_CODE_REMAP = {
        "Lcontrol": 0x001D,
        "Rcontrol": 0xE01D,
        # menu is alt
        "Lmenu": 0x0038,
        "Rmenu": 0xE038,
        "Lwin": 0xE05B,
        "Rwin": 0xE05C,
    }

    # hook 键盘按键按下事件
    def hook_keyboard_down_event(self, event) -> bool:
        logger.debug(f"Hook: {event.Key} {hex(event.ScanCode)}")
        if event.Key in self.SCAN_CODE_REMAP:
            scan_code = self.SCAN_CODE_REMAP[event.Key]
        else:
            scan_code = event.ScanCode
        status, hid_code = (
            self.keyboard_code_data.convert_scan_code_to_hid_code(scan_code)
        )
        if status:
            self.handle_key_press_with_hid_code(hid_code)
        if scan_code not in self.hook_pressed_keys:
            self.hook_pressed_keys.append(scan_code)
        # 如果返回 True 则按键事件会继续传播
        # 如果返回 False 则按键事件会继续传播
        # 因为不希望事件继续传递所以永远返回 False
        return False

    # hook 键盘按键弹起事件
    def hook_keyboard_up_event(self, event) -> bool:
        if event.Key in self.SCAN_CODE_REMAP:
            scan_code = self.SCAN_CODE_REMAP[event.Key]
        else:
            scan_code = event.ScanCode
        status, hid_code = (
            self.keyboard_code_data.convert_scan_code_to_hid_code(scan_code)
        )
        if status:
            self.handle_key_release_with_hid_code(hid_code)
        try:
            self.hook_pressed_keys.remove(scan_code)
        except ValueError:
            pass
        # 如果返回 True 则按键事件会继续传播
        # 如果返回 False 则按键事件会继续传播
        # 因为不希望事件继续传递所以永远返回 False
        return False

    ######################################################################
    # 子窗口执行
    ######################################################################

    # 移动窗口到中心
    def move_dialog_to_center(self, dlg: QDialog) -> None:
        # 确保窗口位置
        wm_pos = self.geometry()
        wm_size = self.size()
        dlg.move(
            int(wm_pos.x() + wm_size.width() / 2 - dlg.width() / 2),
            int(wm_pos.y() + wm_size.height() / 2 - dlg.height() / 2),
        )

    # 执行设置界面
    def execute_settings_dialog(self) -> None:
        # 从配置文件读取配置
        video_config: dict[str, typing.Any] = copy.copy(self.config.video)
        controller_config: dict[str, typing.Any] = copy.copy(
            self.config.controller
        )
        connection_config: dict[str, typing.Any] = copy.copy(
            self.config.connection
        )

        # 传入配置文件的配置
        self.settings_dialog.set_video_config(video_config)
        self.settings_dialog.set_controller_config(controller_config)
        self.settings_dialog.set_connection_config(connection_config)

        # 根据配置文件选择合适的选项
        self.settings_dialog.refresh_with_config()
        # 确保窗口位置
        self.move_dialog_to_center(self.settings_dialog)
        # 执行窗口
        self.settings_dialog.exec()
        # accept_settings 为 True 代表用户按下确定
        if self.settings_dialog.accept_settings:
            try:
                # 获取用户选择的配置
                video_config = self.settings_dialog.get_video_config()
                controller_config = self.settings_dialog.get_controller_config()
                connection_config = self.settings_dialog.get_connection_config()
                # 检查选项是否有效
                if video_config["device"] == "":
                    raise ValueError("Invalid device")
                # 与配置文件合并
                self.config.video.update(video_config)
                self.config.controller.update(controller_config)
                self.config.connection.update(connection_config)
                # 保存配置
                self.save_config()
            except ValueError:
                QMessageBox.critical(
                    self,
                    self.tr("Video Error"),
                    self.tr("Invalid device selected"),
                    QMessageBox.StandardButton.Ok,
                    QMessageBox.StandardButton.NoButton,
                )
            # 尝试按照新配置启动
            # self.video_device_reset()
        pass

    ######################################################################
    # 窗口事件处理
    ######################################################################

    # 全屏状态下鼠标动作事件
    def handle_mouse_on_fullscreen_event(self, x: int, y: int):
        if not self.status.is_enabled("fullscreen"):
            return
        # 常量
        const_pixel = 5
        const_delay_ms = 1000 * 3

        width = self.width()
        height = self.height()
        event_timer = self.timer.get("FULLSCREEN_EVENT_TIMER")

        current_command = self.fullscreen_event_command
        # next_command = current_command
        if y < const_pixel and x < const_pixel:
            # 鼠标在左上角
            next_command = "show_menu_bar"
        elif x > width - const_pixel and y > height - const_pixel:
            # 鼠标在右下角
            next_command = "show_status_bar"
        else:
            # 鼠标在其他地方
            next_command = "hide_all"
        self.fullscreen_event_command = next_command
        # 如果命令发生了变化，说明状态应该改变
        if current_command != next_command:
            event_timer.stop()
            event_timer.start(const_delay_ms)
        pass

    def handle_mouse_move_event(self, event: QMouseEvent) -> None:
        p = event.position().toPoint()
        x, y = p.x(), p.y()
        # 全屏状态下检测鼠标位置
        if self.status.is_enabled("fullscreen"):
            self.handle_mouse_on_fullscreen_event(x, y)
        # 非鼠标捕获的情况下显示光标
        if not self.status.is_enabled("mouse_capture"):
            self.setCursor(Qt.ArrowCursor)
            return
        # 阻止输入的情况下不响应移动事件
        if self.status.is_enabled("block_input"):
            return
        # 暂停鼠标的状态下不响应移动事件
        if self.status.is_enabled("pause_mouse"):
            return
        # 如果选择了隐藏光标或者在相对鼠标模式则隐藏鼠标指针
        if self.status.is_enabled("hide_cursor") or self.status.is_enabled(
            "relative_mode"
        ):
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        self.update_mouse_position_buffer(x, y)

    # 鼠标按下事件
    def handle_mouse_press_event(self, event: QMouseEvent) -> None:
        if (
            not self.status.is_enabled("mouse_capture")
            and event.button() == Qt.LeftButton
            and self.status.is_enabled("camera")
        ):
            self.mouse_capture_triggered()
            return
        if not self.status.is_enabled("mouse_capture"):
            return
        if self.status.is_enabled("block_input"):
            return
        if self.status.is_enabled("pause_mouse"):
            return
        button_code = self.convert_to_button_code(event.button())
        button_state = MouseButtonStateEnum.PRESS
        self.mouse_buffer.set_button(button_code, button_state)
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        if self.status.is_enabled("relative_mode"):
            self.mouse_buffer.clear_point()
        if project_var.debug_mode:
            logger.debug(f"mouse send: {str(self.mouse_buffer)}")
        self.controller_command_send(command, self.mouse_buffer.dup())

    # 鼠标松开事件
    def handle_mouse_release_event(self, event: QMouseEvent) -> None:
        if not self.status.is_enabled("mouse_capture"):
            return
        if self.status.is_enabled("block_input"):
            return
        if self.status.is_enabled("pause_mouse"):
            return
        button_code = self.convert_to_button_code(event.button())
        button_state = MouseButtonStateEnum.RELEASE
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.mouse_buffer.set_button(button_code, button_state)
        if self.status.is_enabled("relative_mode"):
            self.mouse_buffer.clear_point()
        self.controller_command_send(command, self.mouse_buffer.dup())
        self.mouse_buffer.clear_button()

    # 鼠标滚动事件
    def handle_mouse_wheel_event(self, event: QWheelEvent) -> None:
        if not self.status.is_enabled("mouse_capture"):
            return
        if self.status.is_enabled("block_input"):
            return
        if self.status.is_enabled("pause_mouse"):
            return
        y = event.angleDelta().y()
        if y == 120:
            self.mouse_buffer.wheel = MouseWheelStateEnum.DOWN
        elif y == -120:
            self.mouse_buffer.wheel = MouseWheelStateEnum.UP
        else:
            self.mouse_buffer.wheel = MouseWheelStateEnum.STOP
        self.mouse_report_scroll()

    # 检测处理程序自身的快捷键
    def handle_self_hotkey_press(self):
        handle_status = False

        # 如果禁止热键则不处理
        if self.status.is_enabled("disable_hotkey"):
            return handle_status

        # 检测是否按下了 ctrl
        _, ctrl_left = self.keyboard_code_data.convert_key_name_to_hid_code(
            "ctrl_left"
        )
        _, ctrl_right = self.keyboard_code_data.convert_key_name_to_hid_code(
            "ctrl_right"
        )
        if not (
            self.keyboard_key_buffer.is_pressed(ctrl_left)
            or self.keyboard_key_buffer.is_pressed(ctrl_right)
        ):
            return handle_status

        # 检测是否按下了 alt
        _, alt_left = self.keyboard_code_data.convert_key_name_to_hid_code(
            "alt_left"
        )
        _, alt_right = self.keyboard_code_data.convert_key_name_to_hid_code(
            "alt_right"
        )
        if not (
            self.keyboard_key_buffer.is_pressed(alt_left)
            or self.keyboard_key_buffer.is_pressed(alt_right)
        ):
            return handle_status

        # Ctrl+Alt+F11 退出全屏
        _, f11 = self.keyboard_code_data.convert_key_name_to_hid_code("f11")
        if self.status.is_enabled(
            "fullscreen"
        ) and self.keyboard_key_buffer.is_pressed(f11):
            self.fullscreen_state_toggle()
            handle_status = True

        # Ctrl+Alt+F12 关闭鼠标捕获
        _, f12 = self.keyboard_code_data.convert_key_name_to_hid_code("f12")
        if self.status.is_enabled(
            "mouse_capture"
        ) and self.keyboard_key_buffer.is_pressed(f12):
            self.mouse_capture_release_triggered()
            self.reload_controller("mouse")
            self.status_bar_manager.show_message(self.tr("Mouse capture off"))
            handle_status = True

        # Ctrl+Alt+V quick paste
        _, v = self.keyboard_code_data.convert_key_name_to_hid_code("v")
        if self.keyboard_key_buffer.is_pressed(v) and self.status.is_enabled(
            "quick_paste"
        ):
            self.quick_paste_trigger()
            handle_status = True

        # 清空缓冲区确保只响应一次
        if handle_status:
            self.keyboard_key_buffer.clear()
        return handle_status

    # 处理键盘按下事件
    def handle_key_press_with_hid_code(self, hid_code: int) -> None:
        # 指示器按键则更新指示器buffer
        self.update_keyboard_indicator_buffer_with_hid_code(hid_code)
        # 更新键盘buffer
        self.update_keyboard_buffer_with_hid_code(hid_code, KeyStateEnum.PRESS)

        # 检测是否处于阻止输入状态
        if self.status.is_enabled("block_input"):
            return
        if self.status.is_enabled("pause_keyboard"):
            return
        # 检测是否是程序注册的快捷键
        self.handle_self_hotkey_press()
        # 向控制器发送命令
        self.send_keyboard_buffer()

    # 处理键盘松开事件
    def handle_key_release_with_hid_code(self, hid_code: int) -> None:
        if self.status.is_enabled("block_input"):
            return
        if self.status.is_enabled("pause_keyboard"):
            return

        # 更新键盘buffer
        self.update_keyboard_buffer_with_hid_code(
            hid_code, KeyStateEnum.RELEASE
        )

        # 向控制器发送命令
        self.send_keyboard_buffer()
        # 从缓冲区中清理已松开的按键
        self.keyboard_key_buffer.clear_released()

    # 键盘按下事件
    def handle_key_press_with_event(self, event: QKeyEvent) -> bool:
        status: bool = False
        if event.isAutoRepeat():
            return status
        status, hid_code = (
            self.keyboard_code_data.convert_qt_key_event_to_hid_code(event)
        )
        if status:
            self.handle_key_press_with_hid_code(hid_code)
        return status

    # 键盘松开事件
    def handle_key_release_event(self, event: QKeyEvent) -> bool:
        status: bool = False
        if event.isAutoRepeat():
            return status
        status, hid_code = (
            self.keyboard_code_data.convert_qt_key_event_to_hid_code(event)
        )
        if status:
            self.handle_key_release_with_hid_code(hid_code)
        status = True
        return status

    # 窗口改变事件
    def handle_change_event(self, event: QEvent) -> None:
        # 窗口失焦事件
        window_activate_event: list[QEvent.Type] = [
            QEvent.ActivationChange,
            QEvent.WindowActivate,
            QEvent.WindowDeactivate,
        ]
        if event.type() in window_activate_event:
            if not self.isActiveWindow() and self.status.is_enabled(
                "controller"
            ):
                # 窗口失去焦点时释放键盘和鼠标
                # 防止卡键
                self.reload_controller("all")
                pass
        logger.debug(f"window change event: {event}")

    # 关闭事件
    def handle_close_event(self) -> None:
        self.disconnect_controller()
        self.timer.quit_all()
        self.threads.quit_all()

    ######################################################################
    # 覆盖窗口事件
    ######################################################################

    # 鼠标移动事件
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self.handle_mouse_move_event(event)

    # 鼠标按下事件
    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        self.handle_mouse_press_event(event)

    # 鼠标松开事件
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.handle_mouse_release_event(event)

    # 鼠标滚动事件
    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        self.handle_mouse_wheel_event(event)

    # 键盘按下事件
    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        self.handle_key_press_with_event(event)

    # 键盘松开事件
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)
        self.handle_key_release_event(event)

    # 窗口改变事件
    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        self.handle_change_event(event)

    # 关闭事件
    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        self.handle_close_event()


def clear_splash():
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(),
            "onefile_%d_splash_feedback.tmp"
            % int(os.environ["NUITKA_ONEFILE_PARENT"]),
        )
        if os.path.exists(splash_filename):
            os.unlink(splash_filename)


def logger_init():
    logger_fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {name} - {message}"
    log_path = project_binary_directory_path("debug.log")
    # 移除logger handler
    logger.remove()

    if project_var.debug_mode:
        logger.add(sys.stdout, format=logger_fmt, level="DEBUG")
        logger.add(log_path, enqueue=True, level="DEBUG")
        logger.debug("Debug mode enabled")
    else:
        logger.add(sys.stdout, format=logger_fmt, level="INFO")
    logger.info("Logger initialization completed")


def command_line_parser():
    parser = argparse.ArgumentParser(description="USB KVM Client")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Debug mode (default: disable)",
    )

    args = parser.parse_args()
    # 根据 debug 参数设置 debug 模式
    project_var.debug_mode = args.debug
    logger_init()


def os_init():
    system_name = platform.system().lower()
    if system_name == "windows":  # sys.platform == "win32":
        app_id = "open_source_software.usb_kvm_client.gui.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        # 4K分辨率下字体发虚
        # 设置环境变量让渲染使用 freetype
        os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"
        # 设置二进制文件夹为工作目录
        binary_path = project_binary_directory_path()
        os.chdir(binary_path)
    elif system_name == "linux":
        pass
    else:
        pass


def main():
    os_init()
    command_line_parser()
    argv = sys.argv
    app = QApplication(argv)
    # locale = QLocale().system().name().lower()
    translate_files: list[str] = []
    translate_directory_path = project_source_directory_path("translate")
    translate_directory_files: list[str] = os.listdir(translate_directory_path)
    for file_name in translate_directory_files:
        file_path = os.path.join(translate_directory_path, file_name)
        file_ext = os.path.splitext(file_name)[-1]
        if file_ext == ".qm":
            translate_files.append(file_path)
    for file_path in translate_files:
        translator = QTranslator(app)
        if translator.load(file_path):
            app.installTranslator(translator)
    my_window = AppMainWindow()
    my_window.show()
    # QTimer.singleShot(100, my_window.shortcut_status)
    clear_splash()
    return app.exec()


if __name__ == "__main__":
    exit_code: int = main()
    exit(exit_code)
