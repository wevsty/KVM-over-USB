import argparse
import ctypes
import os
import platform
import random
import subprocess
import sys
import tempfile
from typing import Optional

"""
from PySide6 import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtMultimedia import *
from PySide6.QtMultimediaWidgets import *
from PySide6.QtWidgets import *
"""
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import (
    QEvent,
    QLocale,
    QSize,
    Qt,
    QThread,
    QTimer,
    QTranslator,
    QUrl,
    Signal,
    QObject,
    QMutex,
    QMutexLocker,
    QPoint,
    QEventLoop,
)
from PySide6.QtGui import (
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QKeyEvent,
    QPixmap,
    QSurfaceFormat,
    QCursor,
    QMouseEvent,
    QCloseEvent,
)
from PySide6.QtMultimedia import (
    QAudioInput,
    QAudioOutput,
    QCamera,
    QImageCapture,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
    QVideoFrame,
    QVideoSink,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from loguru import logger
import pyWinhook as pyHook
import pythoncom

import controller_device
import project_path
from project_config import MainConfig
from ui.ui_main import MainWindow
from ui.ui_video_device_setup import VideoDeviceConfig, AudioDeviceConfig, VideoDeviceSetupDialog
from ui.ui_controller_device_setup import ControllerDeviceSetupDialog, ControllerDeviceConfig
from ui.ui_custom_key import CustomKeyDialog
from ui.ui_paste_board import PasteBoardDialog
from ui.ui_indicator_lights import IndicatorLightsDialog
from ui.ui_about import AboutDialog
from keyboard_buffer import KeyboardKeyBuffer, KeyStateEnum, KeyboardIndicatorBuffer
from mouse_buffer import MouseStateBuffer, MouseButtonStateEnum, MouseButtonCodeEnum, \
    MouseWheelStateEnum
from data.hex_data import HexData
from data.keyboard_shift_symbol import SHIFT_SYMBOL
from data.keyboard_scancode_to_hid_code import SCANCODE_TO_HID_CODE
from data.keyboard_key_name_to_hid_code import KEY_NAME_TO_HID_CODE


class ControllerEventWorker(QObject):
    command_send_signal = Signal(str, object)
    command_reply_signal = Signal(str, int, object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.mutex = QMutex()
        if controller_device.GLOBAL_CONTROLLER_DEVICE is None:
            controller_device.GLOBAL_CONTROLLER_DEVICE = controller_device.ControllerDevice()
        self.command_send_signal.connect(self.command_event)

    def command_event(self, command: str, buffer: object) -> tuple[str, int, object]:
        """
        command list:
        "device_open"
        "device_close"
        "device_check"
        "device_release"
        "device_reset"
        "keyboard_read"
        "keyboard_write"
        "mouse_relative_write"
        "mouse_absolute_write"
        """
        mutex_locker = QMutexLocker(self.mutex)
        with mutex_locker:
            _, status_code, reply = controller_device.GLOBAL_CONTROLLER_DEVICE.device_event(command, buffer)
            self.command_reply_signal.emit(command, status_code, reply)
        return command, status_code, reply


class MyMainWindow(MainWindow):
    WINDOW_TITLE_STRING: str = "USB KVM Client"
    # 定时器默认延迟
    DEFAULT_TIMER_DELAY: int = 1000

    SCANCODE_REMAP = {
        "Lcontrol": 0x001D,
        "Rcontrol": 0x011D,
        "Lwin": 0x015B,
        "Rwin": 0x015C,
    }

    def __init__(self, parent: Optional[QWidget] = None):
        # 初始化UI
        super().__init__(parent)

        # 初始化状态
        self.status = {
            "screen_height": 0,
            "screen_width": 0,
            "video_recording": False,
            "camera_opened": False,
            "audio_opened": False,
            "controller_opened": False,
            "fullscreen_enabled": False,
            "topmost_enabled": False,
            "mouse_captured": False,
            "mouse_relative_mode": False,
            "hide_cursor_enabled": False,
            "pause_keyboard": False,
            "pause_mouse": False,
            "quick_paste_enabled": True,
            "hook_state": False,
        }

        # 初始化变量
        # self.mutex = QMutex()
        # self.mutex_locker = QMutexLocker(self.mutex)
        self.source_directory: str = project_path.project_source_directory_path()
        self.binary_directory: str = project_path.project_binary_directory_path()
        # 获取显示器分辨率大小
        self.desktop = QGuiApplication.primaryScreen()
        self.status["screen_height"] = self.desktop.availableGeometry().height()
        self.status["screen_width"] = self.desktop.availableGeometry().width()

        # 加载外部数据
        self.keyboard_scancode_to_hid_code = dict()
        self.keyboard_key_name_to_hid_code = dict()
        self.load_external_data()

        # 加载配置文件
        self.config_file: MainConfig | None = None
        self.config_root: dict = dict()
        self.config_ui: dict = dict()
        self.config_video_record: dict = dict()
        self.config_video: dict = dict()
        self.config_audio: dict = dict()
        self.config_controller: dict = dict()
        self.config_mouse: dict = dict()
        self.load_config()

        # 窗口图标
        main_icon: QIcon = QIcon(f"{self.source_directory}/icons/main.ico")
        self.setWindowIcon(main_icon)

        # 初始化菜单图标
        self.init_menu_icon()

        # 子窗口
        self.video_device_setup_dialog = VideoDeviceSetupDialog()
        self.controller_device_setup_dialog = ControllerDeviceSetupDialog()
        self.custom_key_dialog = CustomKeyDialog()
        self.paste_board_dialog = PasteBoardDialog()
        self.indicator_lights_dialog = IndicatorLightsDialog()
        self.about_dialog = AboutDialog()
        # 初始化子窗口图标
        self.init_sub_window_icon()

        # 设备连接
        self.controller_worker_thread: QThread = QThread()
        self.controller_worker_thread.start()
        self.controller_event_worker: ControllerEventWorker = ControllerEventWorker()
        self.controller_event_worker.moveToThread(self.controller_worker_thread)

        # 定时检查控制器连接
        self.device_check_timer = QTimer()
        self.device_check_timer.timeout.connect(self.controller_device_check_connection)
        self.device_check_timer.start(1000)

        # 视频设备
        self.video_device: QMediaDevices | None = None
        self.video_camera: QCamera | None = None
        self.video_capture_session: QMediaCaptureSession = QMediaCaptureSession()
        self.video_sink: QVideoSink = QVideoSink()
        self.video_frame_capture: QImageCapture = QImageCapture()
        self.video_record: QMediaRecorder = QMediaRecorder()

        # 音频设备
        self.audio_in_device: QAudioDevice | None = None
        self.audio_out_device: QAudioDevice | None = None
        self.audio_input: QAudioInput = QAudioInput()
        self.audio_output: QAudioOutput = QAudioOutput()

        # buffer
        self.keyboard_key_buffer: KeyboardKeyBuffer = KeyboardKeyBuffer()
        self.keyboard_indicator_buffer: KeyboardIndicatorBuffer = KeyboardIndicatorBuffer()
        self.mouse_buffer = MouseStateBuffer()

        # 键盘设置
        self.init_shortcut_keys()

        # 键盘钩子
        self.hook_manager = None
        self.pythoncom_timer = QTimer()
        self.hook_pressed_keys = []
        self.init_system_hook()

        # 鼠标设置
        self.mouse_last_pos: None | QPoint = None
        self.relative_mouse_speed = self.config_mouse["mouse_relative_speed"]
        if self.config_mouse["mouse_report_freq"] != 0:
            self.mouse_report_interval = 1000 / self.config_mouse["mouse_report_freq"]
            self.dynamic_mouse_report_interval = False
        else:
            self.mouse_report_interval = 10
            self.dynamic_mouse_report_interval = True
        self.mouse_need_report: bool = False
        self.mouse_report_timer = QTimer()
        self.mouse_report_timer.timeout.connect(self.mouse_timer_report)
        self.mouse_report_timer.start(self.mouse_report_interval)

        # 初始化 Video Widget
        self.video_widget = QVideoWidget()
        self.disconnect_label = QLabel()
        self.init_video_widget()

        # 全屏模式
        self.fullscreen_command = "unknown"
        self.fullscreen_command_timer = QTimer()
        self.fullscreen_command_timer.timeout.connect(self.fullscreen_mouse_command)

        # 状态栏
        self.statusbar_label_ctrl = QLabel()
        self.statusbar_label_shift = QLabel()
        self.statusbar_label_alt = QLabel()
        self.statusbar_label_meta = QLabel()
        self.statusbar_label_caps_lock = QLabel()
        self.statusbar_label_num_lock = QLabel()
        self.statusbar_label_scr_lock = QLabel()
        # 初始化状态栏
        self.init_statusbar()

        # MainWindow accept mouse events
        self.setMouseTracking(True)

        # 检查菜单初始状态
        self.init_menu_checked_state()

        # 绑定信号
        self.init_connect_signal()

        if self.config_video["auto_connect"] is True:
            self.video_device_connect()
        self.controller_device_connect()

    def load_icon(self, file_name: str) -> QIcon:
        return QIcon(f"{self.source_directory}/icons/light/{file_name}.png")

    def load_pixmap(self, file_name: str) -> QPixmap:
        return QPixmap(f"{self.source_directory}/icons/light/{file_name}.png")

    def bool_to_behavior_string(self, value: bool) -> str:
        if value:
            return self.tr("Enable")
        else:
            return self.tr("Disable")

    def load_config(self) -> None:
        try:
            self.config_file = MainConfig(project_path.project_binary_directory_path("config.yaml"))
            self.config_root: dict = self.config_file.data
            self.config_ui: dict = self.config_root["ui"]
            self.config_video_record: dict = self.config_root["video_record"]
            self.config_video: dict = self.config_root["video"]
            self.config_audio: dict = self.config_root["audio"]
            self.config_controller: dict = self.config_root["controller"]
            self.config_mouse: dict = self.config_root["mouse"]
        except Exception as err:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Import config error:\n{}\n").format(err),
            )
            sys.exit(1)

    def save_config(self) -> None:
        # 保存配置文件
        self.config_file.save_to_file()

    def load_external_data(self):
        self.keyboard_scancode_to_hid_code = dict()
        for hex_key, hex_value in SCANCODE_TO_HID_CODE.items():
            self.keyboard_scancode_to_hid_code[HexData.hex_to_int(hex_key)] = HexData.hex_to_int(hex_value)
        self.keyboard_key_name_to_hid_code = dict()
        for key, hex_value in KEY_NAME_TO_HID_CODE.items():
            self.keyboard_key_name_to_hid_code[key] = HexData.hex_to_int(hex_value)

    # 初始化菜单栏图标
    def init_menu_icon(self) -> None:
        # menu_device_menu
        self.action_video_device_setup.setIcon(self.load_icon("import"))
        self.action_video_device_connect.setIcon(self.load_icon("video"))
        self.action_video_device_disconnect.setIcon(self.load_icon("video-off"))
        self.action_controller_device_setup.setIcon(self.load_icon("controller"))
        self.action_device_reload.setIcon(self.load_icon("reload"))
        self.action_device_reset.setIcon(self.load_icon("reset"))
        self.action_minimize.setIcon(self.load_icon("window-minimize"))
        self.action_exit.setIcon(self.load_icon("window-close"))

        # menu_video
        self.action_fullscreen.setIcon(self.load_icon("fullscreen"))
        self.action_resize_window.setIcon(self.load_icon("resize"))
        self.action_topmost.setIcon(self.load_icon("topmost"))
        self.action_keep_ratio.setIcon(self.load_icon("ratio"))
        self.action_capture_frame.setIcon(self.load_icon("capture"))
        self.action_record_video.setIcon(self.load_icon("record"))

        # menu_keyboard
        self.action_pause_keyboard.setIcon(self.load_icon("pause"))
        self.action_reload_keyboard.setIcon(self.load_icon("reload"))
        self.menu_shortcut_keys.setIcon(self.load_icon("keyboard-outline"))
        self.action_custom_key.setIcon(self.load_icon("keyboard-settings-outline"))
        self.action_paste_board.setIcon(self.load_icon("paste"))
        self.action_quick_paste.setIcon(self.load_icon("quick_paste"))
        self.action_system_hook.setIcon(self.load_icon("hook"))
        self.action_sync_indicator.setIcon(self.load_icon("sync"))
        self.action_indicator_light.setIcon(self.load_icon("capslock"))

        # menu_mouse
        self.action_pause_mouse.setIcon(self.load_icon("pause"))
        self.action_reload_mouse.setIcon(self.load_icon("reload"))
        self.action_capture_mouse.setIcon(self.load_icon("mouse"))
        self.action_release_mouse.setIcon(self.load_icon("mouse-off"))
        self.action_relative_mouse.setIcon(self.load_icon("relative"))
        self.action_hide_cursor.setIcon(self.load_icon("cursor"))

        # menu_tools
        self.action_open_windows_device_manager.setIcon(self.load_icon("device"))
        self.action_open_on_screen_keyboard.setIcon(self.load_icon("keyboard-variant"))
        self.action_open_calculator.setIcon(self.load_icon("calculator"))
        self.action_open_snipping_tool.setIcon(self.load_icon("monitor-screenshot"))
        self.action_open_notepad.setIcon(self.load_icon("notebook-edit"))

        # menu_about
        self.action_about.setIcon(self.load_icon("python"))
        self.action_about_qt.setIcon(self.load_icon("qt"))

    def init_sub_window_icon(self):
        self.video_device_setup_dialog.setWindowIcon(self.load_icon("import"))
        self.controller_device_setup_dialog.setWindowIcon(self.load_icon("controller"))
        self.custom_key_dialog.setWindowIcon(self.load_icon("keyboard-outline"))
        self.paste_board_dialog.setWindowIcon(self.load_icon("paste"))
        self.indicator_lights_dialog.setWindowIcon(self.load_icon("capslock"))
        self.about_dialog.setWindowIcon(self.load_icon("python"))

    def init_shortcut_keys(self) -> None:
        self.menu_shortcut_keys.clear()
        for action_name in self.config_root["shortcut_keys"]:
            action = self.menu_shortcut_keys.addAction(action_name)
            action.triggered.connect(
                lambda _checked, triggered_keys=action_name: self.shortcut_key_action(triggered_keys)
            )
        pass

    # 初始化菜单点击状态
    def init_menu_checked_state(self):
        if self.config_video["keep_aspect_ratio"]:
            self.action_keep_ratio.setChecked(True)
        if self.config_ui["quick_paste"]:
            self.status["quick_paste_enabled"] = True
            self.action_quick_paste.setChecked(True)

    def init_video_widget(self):
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

        self.disconnect_label = QLabel()
        self.disconnect_label.setPixmap(self.load_pixmap("disconnected"))
        self.disconnect_label.setAlignment(Qt.AlignCenter)
        self.disconnect_label.setMouseTracking(True)
        self.takeCentralWidget()
        self.setCentralWidget(self.disconnect_label)
        self.disconnect_label.show()

    def init_statusbar(self) -> None:
        self.statusbar_label_ctrl = QLabel()
        self.statusbar_label_shift = QLabel()
        self.statusbar_label_alt = QLabel()
        self.statusbar_label_meta = QLabel()
        self.statusbar_label_caps_lock = QLabel()
        self.statusbar_label_num_lock = QLabel()
        self.statusbar_label_scr_lock = QLabel()
        # 设置字体
        font = QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setBold(True)
        self.statusbar_label_ctrl.setFont(font)
        self.statusbar_label_shift.setFont(font)
        self.statusbar_label_alt.setFont(font)
        self.statusbar_label_meta.setFont(font)
        self.statusbar_label_caps_lock.setFont(font)
        self.statusbar_label_num_lock.setFont(font)
        self.statusbar_label_scr_lock.setFont(font)
        # 设置显示文字
        self.statusbar_label_ctrl.setText("CTRL")
        self.statusbar_label_shift.setText("SHIFT")
        self.statusbar_label_alt.setText("ALT")
        self.statusbar_label_meta.setText("META")
        self.statusbar_label_caps_lock.setText("CAPS")
        self.statusbar_label_num_lock.setText("NUM")
        self.statusbar_label_scr_lock.setText("SCR")
        # 设置颜色
        self.statusbar_label_ctrl.setStyleSheet("color: grey")
        self.statusbar_label_shift.setStyleSheet("color: grey")
        self.statusbar_label_alt.setStyleSheet("color: grey")
        self.statusbar_label_meta.setStyleSheet("color: grey")
        self.statusbar_label_caps_lock.setStyleSheet("color: grey")
        self.statusbar_label_num_lock.setStyleSheet("color: grey")
        self.statusbar_label_scr_lock.setStyleSheet("color: grey")
        # 设置样式
        self.statusBar().setStyleSheet("padding: 0px;")
        # 设置分割线
        self.statusBar().addPermanentWidget(QLabel())
        self.statusBar().addPermanentWidget(self.statusbar_label_ctrl)
        self.statusBar().addPermanentWidget(self.statusbar_label_shift)
        self.statusBar().addPermanentWidget(self.statusbar_label_alt)
        self.statusBar().addPermanentWidget(self.statusbar_label_meta)
        self.statusBar().addPermanentWidget(self.statusbar_label_caps_lock)
        self.statusBar().addPermanentWidget(self.statusbar_label_num_lock)
        self.statusBar().addPermanentWidget(self.statusbar_label_scr_lock)
        self.statusBar().addPermanentWidget(QLabel())
        self.statusbar.reformat()

        # 设置聚焦方式
        self.statusbar_label_ctrl.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_shift.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_alt.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_meta.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_caps_lock.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_num_lock.setFocusPolicy(Qt.NoFocus)
        self.statusbar_label_scr_lock.setFocusPolicy(Qt.NoFocus)

    def init_system_hook(self):
        system_name = platform.system().lower()
        if system_name == "windows":  # sys.platform == "win32":
            pass
        else:
            return
        self.hook_manager = pyHook.HookManager()
        self.hook_manager.KeyDown = self.hook_keyboard_down_event
        self.hook_manager.KeyUp = self.hook_keyboard_up_event
        self.pythoncom_timer = QTimer()
        self.pythoncom_timer.timeout.connect(lambda: pythoncom.PumpWaitingMessages())

    # 初始化信号槽连接
    def init_connect_signal(self) -> None:
        # device
        self.action_video_device_setup.triggered.connect(self.video_device_setup)
        self.action_video_device_connect.triggered.connect(self.video_device_connect)
        self.action_video_device_disconnect.triggered.connect(self.video_device_disconnect)
        self.action_controller_device_setup.triggered.connect(self.controller_device_setup)
        self.action_device_reload.triggered.connect(lambda: self.controller_device_reload("all"))
        self.action_device_reset.triggered.connect(self.controller_device_reset)
        self.action_minimize.triggered.connect(self.window_minimized)
        self.action_exit.triggered.connect(self.window_exit)

        # video
        self.action_fullscreen.triggered.connect(self.fullscreen_state_toggle)
        self.action_resize_window.triggered.connect(self.resize_window_with_video_resolution)
        self.action_topmost.triggered.connect(self.window_topmost_state_toggle)
        self.action_keep_ratio.triggered.connect(self.video_keep_aspect_ratio_toggle)
        self.action_capture_frame.triggered.connect(self.video_frame_capture_trigger)
        self.action_record_video.triggered.connect(self.video_record_trigger)

        # keyboard
        self.action_pause_keyboard.triggered.connect(self.input_pause_state)
        self.action_reload_keyboard.triggered.connect(lambda: self.controller_device_reload("keyboard"))
        self.action_custom_key.triggered.connect(self.custom_key_dialog_show)
        self.custom_key_dialog.custom_key_send_signal.connect(self.custom_key_send)
        self.custom_key_dialog.custom_key_save_signal.connect(self.custom_key_save)
        self.action_paste_board.triggered.connect(lambda: self.paste_board_dialog.exec())
        self.paste_board_dialog.send_string_signal.connect(self.keyboard_send_string)
        self.action_quick_paste.triggered.connect(self.quick_paste_toggle)
        self.action_indicator_light.triggered.connect(self.indicator_lights_action)
        self.indicator_lights_dialog.lock_key_clicked_signal.connect(self.update_keyboard_indicator_buffer)
        self.action_system_hook.triggered.connect(self.system_hook_func)
        self.action_sync_indicator.triggered.connect(self.sync_indicator_action)

        # mouse
        self.action_pause_mouse.triggered.connect(self.input_pause_state)
        self.action_reload_mouse.triggered.connect(lambda: self.controller_device_reload("mouse"))
        self.action_capture_mouse.triggered.connect(self.mouse_capture)
        self.action_release_mouse.triggered.connect(self.mouse_release)
        self.action_relative_mouse.triggered.connect(self.mouse_relative_mouse)
        self.action_hide_cursor.triggered.connect(self.mouse_hide_cursor)

        # tools
        self.action_open_windows_device_manager.triggered.connect(lambda: self.menu_tools_actions("devmgmt.msc"))
        self.action_open_on_screen_keyboard.triggered.connect(lambda: self.menu_tools_actions("osk"))
        self.action_open_calculator.triggered.connect(lambda: self.menu_tools_actions("calc"))
        self.action_open_snipping_tool.triggered.connect(lambda: self.menu_tools_actions("snipping_tool"))
        self.action_open_notepad.triggered.connect(lambda: self.menu_tools_actions("notepad"))

        # about
        self.action_about.triggered.connect(lambda: self.about_dialog.exec())
        self.action_about_qt.triggered.connect(lambda: QApplication.aboutQt())
        # controller event
        self.controller_event_worker.command_reply_signal.connect(self.controller_command_reply)

    # 视频设备配置
    def video_device_setup(self) -> None:
        vc = VideoDeviceConfig()
        vc.from_dict(self.config_video)
        ac = AudioDeviceConfig()
        ac.from_dict(self.config_audio)
        # 传入配置文件的配置
        self.video_device_setup_dialog.set_video_config(vc)
        self.video_device_setup_dialog.set_audio_config(ac)

        # 确保窗口位置
        wm_pos = self.geometry()
        wm_size = self.size()
        self.video_device_setup_dialog.move(
            int(wm_pos.x() + wm_size.width() / 2 - self.video_device_setup_dialog.width() / 2),
            int(wm_pos.y() + wm_size.height() / 2 - self.video_device_setup_dialog.height() / 2),
        )
        # 执行窗口
        status_code = self.video_device_setup_dialog.exec()
        # 用户按下确定时 status_code != 0
        if status_code != 0:
            try:
                # 获取用户选择的配置
                vc = self.video_device_setup_dialog.get_video_config()
                ac = self.video_device_setup_dialog.get_audio_config()
                # 检查选项是否有效
                if vc.device == "":
                    raise ValueError("Invalid device")
                # 与配置文件合并
                self.config_video.update(vc.to_dict())
                self.config_audio.update(ac.to_dict())
                # 保存配置
                self.save_config()
            except ValueError:
                QMessageBox.critical(self, self.tr("Video Error"), self.tr("Invalid device selected"))
            # 尝试按照新配置启动
            self.video_device_reset()
        else:
            pass

    def video_camera_error_occurred(self, error: QCamera.Error, _string: str) -> None:
        error_s = (
                f"Device: {self.video_device.description()}\n"
                f"Returned: {error}\n"
                + self.tr("Device disconnected")
        )
        self.video_device_disconnect()
        QMessageBox.critical(self, self.tr("Device Error"), error_s)

    def video_frame_changed(self, frame: QVideoFrame) -> None:
        self.video_widget.videoSink().setVideoFrame(frame)
        self.video_widget.update()
        self.video_widget.repaint()

    # 视频设备初始化
    def video_device_init(self) -> bool:
        return_status: bool = False
        # 寻找指定视频设备
        video_device_description = self.config_video["device"]
        if video_device_description == "":
            QMessageBox.critical(self, self.tr("Video Error"), self.tr("Target video device is empty"))
            return return_status
        cameras = QMediaDevices.videoInputs()
        for camera in cameras:
            if camera.description() == video_device_description:
                self.video_device = camera
                break
        if self.video_device is None:
            QMessageBox.critical(self, self.tr("Video Error"), self.tr("Target video device not found"))
            return return_status
        # 设置摄像头配置
        self.video_camera = QCamera(self.video_device)
        camera_set_done = False
        for i in self.video_device.videoFormats():
            resolution_x = i.resolution().width()
            resolution_y = i.resolution().height()
            pixel_format = i.pixelFormat().name.split("_")[1]
            if (
                    resolution_x == self.config_video["resolution_x"]
                    and resolution_y == self.config_video["resolution_y"]
                    and pixel_format == self.config_video["format"]
            ):
                self.video_camera.setCameraFormat(i)
                camera_set_done = True
                break
        if camera_set_done is False:
            QMessageBox.critical(self, self.tr("Video Error"),
                                 self.tr("Unsupported combination of resolution or format"))
            return return_status
        # 配置音频
        if self.config_audio["audio_support"] is True:
            in_devices = QMediaDevices.audioInputs()
            out_devices = QMediaDevices.audioOutputs()
            in_device_name = self.config_audio["audio_device_in"]
            out_device_name = self.config_audio["audio_device_out"]
            if in_device_name == self.tr("auto"):
                in_device = QMediaDevices.defaultAudioInput()
            else:
                in_device = None
                for i in in_devices:
                    if i.description() == in_device_name:
                        in_device = i
                        break

            if out_device_name == self.tr("auto"):
                out_device = QMediaDevices.defaultAudioOutput()
            else:
                out_device = None
                for i in out_devices:
                    if i.description() == out_device_name:
                        out_device = i
                        break
            if in_device is None or out_device is None:
                QMessageBox.critical(self, self.tr("Video Error"),
                                     self.tr("Audio device not found"))
                return return_status
            self.audio_in_device = in_device
            self.audio_out_device = out_device
        # 启动摄像头
        self.video_camera.errorOccurred.connect(self.video_camera_error_occurred)
        self.video_camera.start()
        if not self.video_camera.isActive():
            self.status["camera_opened"] = False
            QMessageBox.critical(self, self.tr("Video Error"),
                                 self.tr("Video device connect failed"))
            return return_status
        else:
            self.status["camera_opened"] = True
        # 设置视频捕捉
        self.video_capture_session = QMediaCaptureSession()
        self.video_sink = QVideoSink()
        self.video_frame_capture = QImageCapture(self.video_camera)
        self.video_capture_session.setCamera(self.video_camera)
        self.video_capture_session.setImageCapture(self.video_frame_capture)
        self.video_capture_session.setVideoSink(self.video_sink)
        # self.video_capture_session.setVideoOutput(self.videoWidget)
        self.video_sink.videoFrameChanged.connect(self.video_frame_changed)

        self.video_frame_capture.setQuality(QImageCapture.Quality.VeryHighQuality)
        self.video_frame_capture.setFileFormat(QImageCapture.FileFormat.PNG)
        self.video_frame_capture.imageCaptured.connect(
            self.video_frame_capture_done
        )

        self.video_record = QMediaRecorder(self.video_camera)
        self.video_capture_session.setRecorder(self.video_record)
        self.video_record.setQuality(
            getattr(QMediaRecorder.Quality, self.config_video_record["quality"])
        )
        self.video_record.setMediaFormat(QMediaFormat.FileFormat.MPEG4)
        self.video_record.setEncodingMode(
            getattr(
                QMediaRecorder.EncodingMode, self.config_video_record["encoding_mode"]
            )
        )
        self.video_record.setVideoBitRate(self.config_video_record["encoding_bitrate"])
        self.video_record.setVideoFrameRate(self.config_video_record["frame_rate"])
        self.video_record.setVideoResolution(QSize())
        self.status["video_recording"] = False
        # 设置音频捕捉
        if self.config_audio["audio_support"] is True:
            self.audio_input = QAudioInput(self.audio_in_device)
            self.audio_output = QAudioOutput(self.audio_out_device)
            self.audio_input.setVolume(1)
            self.audio_output.setVolume(1)
            self.audio_input.setMuted(False)
            self.audio_output.setMuted(False)
            self.capture_session.setAudioInput(self.audio_input)
            self.capture_session.setAudioOutput(self.audio_output)
            self.status["audio_opened"] = True
            # self.video_record.setAudioBitRate(16)
            # self.video_record.setAudioSampleRate(48000)
            # self.video_record.record()
            logger.debug("Audio device ok")
        else:
            self.audio_input = QAudioInput()
            self.audio_output = QAudioOutput()
            self.status["audio_opened"] = False
        return_status = True
        return return_status

    # 启用视频设备
    def video_device_connect(self, center=False) -> None:
        if not self.video_device_init():
            return
        if not self.status["fullscreen_enabled"]:
            self.resize_window_with_video_resolution(center=center)
        fps = self.video_camera.cameraFormat().maxFrameRate()
        # self.device_event_handle("video_ok")
        self.takeCentralWidget()
        self.setCentralWidget(self.video_widget)
        self.disconnect_label.hide()
        self.video_widget.show()
        self.setWindowTitle(
            f"{self.WINDOW_TITLE_STRING} - {self.config_video["resolution_x"]}x{self.config_video["resolution_y"]} @ {fps:.1f}"
        )
        if self.dynamic_mouse_report_interval:
            self.mouse_report_interval = 1000 / fps
            self._mouse_report_timer.setInterval(self.mouse_report_interval)

    # 停用视频设备
    def video_device_disconnect(self) -> None:
        if self.status["camera_opened"]:
            self.video_camera.stop()
            self.video_camera.setActive(False)
            self.video_camera.deleteLater()
            self.video_capture_session.deleteLater()
            self.video_frame_capture.deleteLater()
            self.video_record.deleteLater()
            self.status["camera_opened"] = False
        if self.status["audio_opened"]:
            self.audio_input.deleteLater()
            self.audio_output.deleteLater()
            self.audio_in_device = None
            self.audio_out_device = None
            self.status["audio_opened"] = False
        # self.device_event_handle("video_close")
        self.takeCentralWidget()
        self.setCentralWidget(self.disconnect_label)
        self.video_widget.hide()
        self.disconnect_label.show()
        self.setWindowTitle(self.WINDOW_TITLE_STRING)

    # 重新启动视频设备
    def video_device_reset(self) -> None:
        self.video_device_disconnect()
        self.video_device_connect()

    # 全屏模式
    def fullscreen_state_toggle(self) -> None:
        self.status["fullscreen_enabled"] = not self.status["fullscreen_enabled"]
        if self.status["fullscreen_enabled"]:
            if self.config_ui["fullscreen_state_alert"]:
                alert_checkbox = QCheckBox(self.tr("Don't show again"))
                alert_window = QMessageBox(self)
                alert_window.setWindowTitle(self.tr("Fullscreen mode alert"))
                alert_window.setText(
                    self.tr("Press Ctrl+Alt+F11 to toggle fullscreen\n") +
                    self.tr("Stay cursor at left top corner to show toolbar")
                )
                alert_window.setCheckBox(alert_checkbox)
                alert_window.exec()
                if alert_window.checkBox().isChecked() is True:
                    self.config_ui["fullscreen_state_alert"] = False
                    self.save_config()
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
            self.action_resize_window.setEnabled(False)
            self.statusBar().hide()
            self.menuBar().hide()
        else:
            self.showNormal()
            self.action_fullscreen.setChecked(False)
            self.action_resize_window.setEnabled(True)
            self.statusBar().show()
            self.menuBar().show()

    def fullscreen_mouse_command(self):
        command = self.fullscreen_command
        if command == "show_menubar":
            if self.menuBar().isHidden():
                self.menuBar().show()
        elif command == "show_statusbar":
            if self.statusBar().isHidden():
                self.statusBar().show()
        elif command == "hide_all":
            if not self.menuBar().isHidden():
                self.menuBar().hide()
            if not self.statusBar().isHidden():
                self.statusBar().hide()
        else:
            pass
        self.fullscreen_command_timer.stop()
        pass

    # 全屏状态下鼠标动作事件
    def fullscreen_mouse_event(self, x: int, y: int):
        if not self.status["fullscreen_enabled"]:
            return
        const_pixel = 5
        width = self.width()
        height = self.height()

        if y < const_pixel and x < const_pixel:
            # 鼠标在左上角
            self.fullscreen_command = "show_menubar"
            self.fullscreen_command_timer.start(self.DEFAULT_TIMER_DELAY)
        elif x > width - const_pixel and y > height - const_pixel:
            # 鼠标在右下角
            self.fullscreen_command = "show_statusbar"
            self.fullscreen_command_timer.start(self.DEFAULT_TIMER_DELAY)
        else:
            # 鼠标在其他地方
            self.fullscreen_command = "hide_all"
            self.fullscreen_command_timer.start(self.DEFAULT_TIMER_DELAY)

    # 通过视频设备分辨率调整窗口大小
    def resize_window_with_video_resolution(self, center=True) -> None:
        if self.status["fullscreen_enabled"]:
            return
        menu_bar_height = self.menubar.height()
        status_bar_height = self.statusbar.height()
        add_height = menu_bar_height + status_bar_height

        retained_height = 9 * 5
        retained_width = 16 * 5
        recommend_height = self.config_video["resolution_y"] + add_height
        recommend_width = self.config_video["resolution_x"]
        if ((self.status["screen_height"] - retained_height > recommend_height)
                and (self.status["screen_width"] - retained_width > recommend_width)):
            # 如果屏幕大小足够
            self.showNormal()
            self.resize(
                recommend_width,
                recommend_height,
            )
        else:
            # 如屏幕大小不够
            while not ((self.status["screen_height"] - retained_height > recommend_height)
                       and (self.status["screen_width"] - retained_width > recommend_width)):
                recommend_height = int(recommend_height * 1 / 4)
                recommend_width = int(recommend_width * 1 / 4)
            self.showNormal()
            self.resize(
                recommend_width,
                recommend_height,
            )
            self.showMaximized()
        if center:
            qr = self.frameGeometry()
            cp = QGuiApplication.primaryScreen().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        if self.config_video["keep_aspect_ratio"]:
            self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        else:
            self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)

    # 切换保持窗口在最前
    def window_topmost_state_toggle(self):
        self.status["topmost_enabled"] = not self.status["topmost_enabled"]
        current_window_flag = self.windowFlags()
        if self.status["topmost_enabled"]:
            self.windowHandle().setFlags(
                current_window_flag | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint
            )
        else:
            self.windowHandle().setFlags(
                current_window_flag & ~Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint
            )
        self.statusBar().showMessage(
            self.tr("Window topmost: ") + self.bool_to_behavior_string(self.status["topmost_enabled"])
        )
        self.action_topmost.setChecked(self.status["topmost_enabled"])

    # 保持比例拉伸
    def video_keep_aspect_ratio_toggle(self):
        self.config_video["keep_aspect_ratio"] = not self.config_video[
            "keep_aspect_ratio"
        ]
        if self.config_video["keep_aspect_ratio"]:
            self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
            self.action_keep_ratio.setChecked(True)
        else:
            self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)
            self.action_keep_ratio.setChecked(False)
        self.statusBar().showMessage(
            self.tr("Keep aspect ratio: ") +
            self.bool_to_behavior_string(self.config_video["keep_aspect_ratio"])
        )
        self.save_config()

    # 视频帧捕捉完成
    def video_frame_capture_done(self, capture_id: int, preview: QImage) -> None:
        logger.debug("frame_captured", capture_id)
        file_name = QFileDialog.getSaveFileName(
            self,
            self.tr("Image Save"),
            "untitled.png",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )[0]
        if file_name == "":
            return
        preview.save(file_name)
        self.statusBar().showMessage(self.tr("Image saved to") + f" {file_name}")

    # 保存当前帧命令触发
    def video_frame_capture_trigger(self) -> None:
        if self.status["camera_opened"]:
            self.video_frame_capture.capture()
        logger.debug("video_frame_capture_trigger triggered")

    def video_record_trigger(self) -> None:
        if not self.status["camera_opened"]:
            return
        if (
                self.video_record.recorderState()
                == QMediaRecorder.RecorderState.RecordingState
        ):
            self.video_record.stop()
        if self.status["video_recording"]:
            self.video_record.stop()
            self.status["video_recording"] = False
            self.action_record_video.setText(self.tr("Record video"))
            self.action_record_video.setChecked(False)
            self.statusBar().showMessage(self.tr("Video recording stopped"))
        else:
            file_name = QFileDialog.getSaveFileName(
                self,
                self.tr("Video save"),
                "output.mp4",
                "Video (*.mp4)",
            )[0]
            if file_name == "":
                return
            self.video_record.setOutputLocation(QUrl.fromLocalFile(file_name))
            self.video_record.record()
            self.status["video_recording"] = True
            self.action_record_video.setText(self.tr("Stop recording"))
            self.action_record_video.setChecked(True)
            self.statusBar().showMessage(self.tr("Video recording started"))

    def controller_command_reply(self, command: str, status: int, data: object):
        ignored_command = [
            "device_release",
            "device_reset",
            "mouse_relative_write",
            "mouse_absolute_write",
            "keyboard_write"
        ]
        if command == "device_open":
            if status == 0:
                # open 成功
                self.status["controller_opened"] = True
                self.statusBar().showMessage(self.tr("Controller connected"))
                # 连接成功发送读取键盘指示灯信号
                self.controller_event_worker.command_send_signal.emit("keyboard_read", None)
            else:
                self.status["controller_opened"] = False
                self.statusBar().showMessage(self.tr("Controller connect failure"))
        elif command == "device_close":
            self.status["controller_opened"] = False
        elif command == "device_check":
            if status != 0:
                # 检查连接返回失败
                self.controller_device_disconnect()
                self.controller_device_connect()
        elif command == "keyboard_read":
            if status == 0:
                logger.debug(f"keyboard indicator read succeed")
                self.keyboard_indicator_buffer.from_dict(data)
                self.update_status_bar()
            else:
                logger.debug(f"keyboard indicator read failed")
        elif command in ignored_command:
            pass
        else:
            logger.debug(f"Unhandled command reply: {command}")
            pass

    def controller_device_setup(self):
        cc = ControllerDeviceConfig()
        cc.port = self.config_controller["port"]
        cc.baud = self.config_controller["baud"]
        cc.screen_x = self.config_controller["screen_x"] = self.config_video["resolution_x"]
        cc.screen_y = self.config_controller["screen_y"] = self.config_video["resolution_y"]

        # 确保窗口位置
        wm_pos = self.geometry()
        wm_size = self.size()
        self.video_device_setup_dialog.move(
            int(wm_pos.x() + wm_size.width() / 2 - self.video_device_setup_dialog.width() / 2),
            int(wm_pos.y() + wm_size.height() / 2 - self.video_device_setup_dialog.height() / 2),
        )
        # 执行窗口
        self.controller_device_setup_dialog.set_controller_device_config(cc)
        status_code = self.controller_device_setup_dialog.exec()
        if status_code != 0:
            cc = self.controller_device_setup_dialog.get_controller_device_config()
            self.config_controller["port"] = cc.port
            self.config_controller["baud"] = cc.baud
            self.save_config()
            self.controller_device_disconnect()
            self.controller_device_connect()

    # 连接设备
    def controller_device_connect(self):
        controller_device.GLOBAL_CONTROLLER_DEVICE.device_init(
            self.config_controller["port"],
            self.config_controller["baud"],
            self.config_video["resolution_x"],
            self.config_video["resolution_y"]
        )
        self.controller_event_worker.command_send_signal.emit('device_open', None)

    # 断开设备
    def controller_device_disconnect(self):
        self.controller_event_worker.command_send_signal.emit('device_close', None)

    # 检查连接
    def controller_device_check_connection(self):
        self.controller_event_worker.command_send_signal.emit('device_check', None)

    # 重新载入设备
    def controller_device_reload(self, release_type: str):
        if release_type == "keyboard":
            self.controller_event_worker.command_send_signal.emit('device_release', "keyboard")
            self.keyboard_key_buffer.clear()
        elif release_type == "mouse":
            self.controller_event_worker.command_send_signal.emit('device_release', "mouse")
            self.mouse_buffer.clear()
        else:
            self.controller_event_worker.command_send_signal.emit('device_release', "all")
            self.keyboard_key_buffer.clear()
            self.mouse_buffer.clear()
            self.controller_device_disconnect()
            self.controller_device_connect()

    # 重置设备
    def controller_device_reset(self):
        self.controller_event_worker.command_send_signal.emit('device_reset', None)
        self.keyboard_key_buffer.clear()
        self.mouse_buffer.clear()

    # 最小化窗口
    def window_minimized(self) -> None:
        self.showMinimized()

    # 关闭窗口
    def window_exit(self) -> None:
        self.close()

    # 设置输入转发状态
    def input_pause_state(self):
        if self.action_pause_keyboard.isChecked() is True:
            self.status["pause_keyboard"] = True
        else:
            self.status["pause_keyboard"] = False

        if self.action_pause_mouse.isChecked() is True:
            self.status["pause_mouse"] = True
        else:
            self.status["pause_mouse"] = False

    def shortcut_key_send(self, keys: list[str]):
        key_code_list = list()
        for key_name in keys:
            key_code = self.keyboard_key_name_to_hid_code.get(key_name, 0)
            if key_code == 0:
                continue
            key_code_list.append(key_code)
        for key_code in key_code_list:
            self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.PRESS)
        self.random_sleep()
        for key_code in key_code_list:
            self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.RELEASE)

    def shortcut_key_action(self, action_name: str):
        for keys_name in self.config_root["shortcut_keys"]:
            if action_name == keys_name:
                send_buffer = self.config_root["shortcut_keys"][action_name]
                self.shortcut_key_send(send_buffer)
                break
            pass
        pass

    def custom_key_dialog_show(self):
        self.custom_key_dialog.exec()

    def custom_key_send(self, keys: list[str]):
        self.shortcut_key_send(keys)

    def custom_key_save(self, name: str, keys: list[str]):
        custom_key_data = {
            name: keys
        }
        self.config_root["shortcut_keys"].update(custom_key_data)
        self.save_config()
        self.init_shortcut_keys()

    # 使用键盘发送字符串
    def keyboard_send_string(self, data: str):
        shift_hid_code: int = self.keyboard_key_name_to_hid_code.get("shift", 0)
        assert shift_hid_code != 0
        # 强制关闭 capslock
        if self.keyboard_indicator_buffer.caps_lock:
            self.update_keyboard_indicator_buffer("caps_lock")
        shift_flag = False
        for character in data:
            if character.isascii() is False:
                logger.critical(f"Character not supported: {character}")
                continue
            # 如果是需要shift的符号
            if character in SHIFT_SYMBOL:
                shift_flag = True
            # 如果是大写字母
            if character.isupper():
                shift_flag = True
            key_code = self.keyboard_key_name_to_hid_code.get(character, 0)
            if key_code == 0:
                logger.critical(f"character key code not found: {character}")
                continue
            if shift_flag:
                self.update_keyboard_buffer_with_hid_code(shift_hid_code, KeyStateEnum.PRESS)
                self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.PRESS)

                self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.RELEASE)
                self.update_keyboard_buffer_with_hid_code(shift_hid_code, KeyStateEnum.RELEASE)
                self.sleep(self.config_root["paste_board"]["interval"])
            else:
                self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.PRESS)
                self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.RELEASE)
                self.sleep(self.config_root["paste_board"]["interval"])

    # 快速粘贴功能开关切换
    def quick_paste_toggle(self):
        self.status["quick_paste_enabled"] = not self.status["quick_paste_enabled"]
        self.action_quick_paste.setChecked(self.status["quick_paste_enabled"])
        self.statusBar().showMessage(
            self.tr("Quick paste: ") + self.bool_to_behavior_string(self.status["quick_paste_enabled"])
        )

    def quick_paste_trigger(self):
        # 获取剪贴板内容
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if len(text) == 0:
            self.statusBar().showMessage(self.tr("Clipboard is empty"))
            return
        self.statusBar().showMessage(
            self.tr("Quick pasting") + f" {len(text)} " + self.tr("characters")
        )
        self.clear_keyboard_key_buffer()
        self.keyboard_send_string(text)

    # 发送请求同步键盘指示灯状态
    def sync_indicator_action(self):
        self.clear_keyboard_indicator_buffer()

    def indicator_lights_action(self):
        if self.indicator_lights_dialog.isVisible():
            self.indicator_lights_dialog.activateWindow()
            return
        add_height = 60
        wm_pos = self.geometry()
        wm_size = self.size()
        self.indicator_lights_dialog.move(
            wm_pos.x() + (wm_size.width() - self.indicator_lights_dialog.width()),
            wm_pos.y()
            + (wm_size.height() - self.indicator_lights_dialog.height() - add_height),
        )
        self.indicator_lights_dialog.update_buffer(self.keyboard_indicator_buffer)
        self.indicator_lights_dialog.refresh_status_from_buffer()
        self.indicator_lights_dialog.exec()

    # 系统钩子
    def system_hook_func(self):
        system_name = platform.system().lower()
        if system_name == "windows":  # sys.platform == "win32":
            pass
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("system hook only supports windows")
            )
            return
        self.status["hook_state"] = not self.status["hook_state"]
        self.action_system_hook.setChecked(self.status["hook_state"])
        self.statusBar().showMessage(
            self.tr("System hook: ") + self.bool_to_behavior_string(self.status["hook_state"])
        )
        if self.status["hook_state"]:
            self.pythoncom_timer.start(5)
            self.hook_manager.HookKeyboard()
        else:
            self.hook_manager.UnhookKeyboard()
            self.pythoncom_timer.stop()

    # 捕获鼠标功能
    def mouse_capture(self) -> None:
        self.status["mouse_captured"] = True
        self.statusBar().showMessage(
            self.tr("Mouse capture on (Press Ctrl+Alt+F12 to release)")
        )

    # 释放鼠标功能
    def mouse_release(self) -> None:
        self.status["mouse_captured"] = False

    def mouse_relative_mouse(self):
        self.status["mouse_relative_mode"] = not self.status["mouse_relative_mode"]
        self.action_relative_mouse.setChecked(self.status["mouse_relative_mode"])
        self.statusBar().showMessage(
            self.tr("Relative mouse: ") + self.bool_to_behavior_string(self.status["mouse_relative_mode"])
        )

    # 隐藏指针
    def mouse_hide_cursor(self) -> None:
        self.status["hide_cursor_enabled"] = not self.status["hide_cursor_enabled"]
        if self.status["hide_cursor_enabled"]:
            self.action_hide_cursor.setChecked(True)
        else:
            self.action_hide_cursor.setChecked(False)
        self.statusBar().showMessage(
            self.tr("Hide cursor when capture mouse: ")
            + self.bool_to_behavior_string(self.status["hide_cursor_enabled"])
        )

    @staticmethod
    def menu_tools_actions(action_name: str):
        system_name = platform.system().lower()
        if system_name == "windows":  # sys.platform == "win32":
            pass
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("system hook only supports windows")
            )
            return
        if action_name == "devmgmt.msc":
            subprocess.Popen("devmgmt.msc", shell=True)
        elif action_name == "osk":
            subprocess.Popen("osk.exe")
        elif action_name == "calc":
            subprocess.Popen("calc.exe")
        elif action_name == "snipping_tool":
            subprocess.Popen("SnippingTool.exe")
        elif action_name == "notepad":
            subprocess.Popen("notepad.exe")
        else:
            pass

    # 随机延迟
    @staticmethod
    def random_sleep(min_interval: int = 0, max_interval: int = 100):
        random_sleep_time = int(random.uniform(min_interval, max_interval))
        if random_sleep_time > 0:
            loop = QEventLoop()
            QTimer.singleShot(random_sleep_time, loop.quit)
            loop.exec()

    # 固定延迟
    @staticmethod
    def sleep(interval: int = 1):
        interval = int(interval)
        if interval > 0:
            loop = QEventLoop()
            QTimer.singleShot(interval, loop.quit)
            loop.exec()

    def update_status_bar(self):
        ctrl_left = self.keyboard_key_name_to_hid_code.get("ctrl_left", 0)
        ctrl_right = self.keyboard_key_name_to_hid_code.get("ctrl_right", 0)
        if self.keyboard_key_buffer.key_state(ctrl_left) == KeyStateEnum.PRESS or self.keyboard_key_buffer.key_state(
                ctrl_right) == KeyStateEnum.PRESS:
            self.statusbar_label_ctrl.setStyleSheet("color: black")
        else:
            self.statusbar_label_ctrl.setStyleSheet("color: grey")

        shift_left = self.keyboard_key_name_to_hid_code.get("shift_left", 0)
        shift_right = self.keyboard_key_name_to_hid_code.get("shift_right", 0)
        if self.keyboard_key_buffer.key_state(shift_left) == KeyStateEnum.PRESS or self.keyboard_key_buffer.key_state(
                shift_right) == KeyStateEnum.PRESS:
            self.statusbar_label_shift.setStyleSheet("color: black")
        else:
            self.statusbar_label_shift.setStyleSheet("color: grey")

        alt_left = self.keyboard_key_name_to_hid_code.get("alt_left", 0)
        alt_right = self.keyboard_key_name_to_hid_code.get("alt_right", 0)
        if self.keyboard_key_buffer.key_state(alt_left) == KeyStateEnum.PRESS or self.keyboard_key_buffer.key_state(
                alt_right) == KeyStateEnum.PRESS:
            self.statusbar_label_alt.setStyleSheet("color: black")
        else:
            self.statusbar_label_alt.setStyleSheet("color: grey")

        win_left = self.keyboard_key_name_to_hid_code.get("win_left", 0)
        win_right = self.keyboard_key_name_to_hid_code.get("win_right", 0)
        if self.keyboard_key_buffer.key_state(win_left) == KeyStateEnum.PRESS or self.keyboard_key_buffer.key_state(
                win_right) == KeyStateEnum.PRESS:
            self.statusbar_label_meta.setStyleSheet("color: black")
        else:
            self.statusbar_label_meta.setStyleSheet("color: grey")

        if self.keyboard_indicator_buffer.num_lock:
            self.statusbar_label_num_lock.setStyleSheet("color: black")
        else:
            self.statusbar_label_num_lock.setStyleSheet("color: grey")

        if self.keyboard_indicator_buffer.caps_lock:
            self.statusbar_label_caps_lock.setStyleSheet("color: black")
        else:
            self.statusbar_label_caps_lock.setStyleSheet("color: grey")

        if self.keyboard_indicator_buffer.scroll_lock:
            self.statusbar_label_scr_lock.setStyleSheet("color: black")
        else:
            self.statusbar_label_scr_lock.setStyleSheet("color: grey")

    # 更新键盘缓冲区(hid_code)
    def update_keyboard_buffer_with_hid_code(self, hid_code: int, state: KeyStateEnum) -> None:
        if state == KeyStateEnum.PRESS:
            self.keyboard_key_buffer.key_press(hid_code)
        else:
            self.keyboard_key_buffer.key_release(hid_code)
        self.controller_event_worker.command_send_signal.emit(
            "keyboard_write",
            self.keyboard_key_buffer.dup()
        )
        self.keyboard_key_buffer.clear_released()
        self.update_status_bar()

    # 更新键盘缓冲区(scancode)
    def update_keyboard_buffer_with_scancode(self, scancode: int, state: KeyStateEnum) -> None:
        hid_code = self.keyboard_scancode_to_hid_code.get(scancode, 0)
        if hid_code == 0:
            logger.warning(f"Unknown keyboard scancode: {scancode}")
            return
        self.update_keyboard_buffer_with_hid_code(hid_code, state)

    def update_keyboard_indicator_buffer(self, key_name: str) -> None:
        if key_name == "num_lock":
            key_code = self.keyboard_key_name_to_hid_code.get("num_lock", 0)
            assert key_code != 0
            self.keyboard_indicator_buffer.num_lock = not self.keyboard_indicator_buffer.num_lock
        elif key_name == "caps_lock":
            key_code = self.keyboard_key_name_to_hid_code.get("caps_lock", 0)
            assert key_code != 0
            self.keyboard_indicator_buffer.caps_lock = not self.keyboard_indicator_buffer.caps_lock
        elif key_name == "scroll_lock":
            key_code = self.keyboard_key_name_to_hid_code.get("scroll_lock", 0)
            assert key_code != 0
            self.keyboard_indicator_buffer.scroll_lock = not self.keyboard_indicator_buffer.scroll_lock
        else:
            logger.error(f"Error key name: {key_name}")
            raise ValueError(f"Error key name: {key_name}")
        self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.PRESS)
        self.update_keyboard_buffer_with_hid_code(key_code, KeyStateEnum.RELEASE)
        self.update_status_bar()

    # 清空键盘按键缓冲区
    def clear_keyboard_key_buffer(self):
        self.keyboard_key_buffer.clear()
        self.controller_event_worker.command_send_signal.emit(
            "keyboard_write",
            self.keyboard_key_buffer.dup()
        )

    # 清空键盘指示器缓冲区
    def clear_keyboard_indicator_buffer(self):
        self.keyboard_indicator_buffer.clear()
        self.controller_event_worker.command_send_signal.emit("keyboard_read", None)

    # 更新鼠标坐标缓冲区(绝对坐标模式)
    def update_mouse_absolute_position(self, x: int, y: int):
        self.mouse_last_pos = None
        if not self.status["camera_opened"]:
            x_res = self.disconnect_label.width()
            y_res = self.disconnect_label.height()
            width = self.disconnect_label.width()
            height = self.disconnect_label.height()
            x_pos = self.disconnect_label.pos().x()
            y_pos = self.disconnect_label.pos().y()
        else:
            x_res = self.config_video["resolution_x"]
            y_res = self.config_video["resolution_y"]
            width = self.video_widget.width()
            height = self.video_widget.height()
            x_pos = self.video_widget.pos().x()
            y_pos = self.video_widget.pos().y()
        x_diff = 0
        y_diff = 0
        if self.config_video["keep_aspect_ratio"]:
            cam_scale = y_res / x_res
            finder_scale = height / width
            if finder_scale > cam_scale:
                x_diff = 0
                y_diff = height - width * cam_scale
            elif finder_scale < cam_scale:
                x_diff = width - height / cam_scale
                y_diff = 0
        x_hid = (x - x_diff / 2 - x_pos) / (width - x_diff)
        y_hid = (y - y_diff / 2 - y_pos) / (height - y_diff)
        x_hid = max(min(x_hid, 1), 0)
        y_hid = max(min(y_hid, 1), 0)
        self.mouse_buffer.set_point(x_hid, y_hid)
        self.statusBar().showMessage(f"X={x_hid * x_res:.0f}, Y={y_hid * y_res:.0f}")
        # logger.debug(f"X={x_hid * x_res:.0f}, Y={y_hid * y_res:.0f}")

    # 更新鼠标坐标缓冲区(相对坐标模式)
    def update_mouse_relative_position(self, x: int, y: int):
        middle_pos = self.mapToGlobal(QPoint(int(self.width() / 2), int(self.height() / 2)))
        mouse_pos = QCursor.pos()
        if self.mouse_last_pos is not None:
            rel_x, rel_y = self.mouse_buffer.get_point()
            rel_x += (
                             mouse_pos.x() - self.mouse_last_pos.x()
                     ) * self.relative_mouse_speed
            rel_y += (
                             mouse_pos.y() - self.mouse_last_pos.y()
                     ) * self.relative_mouse_speed
            self.mouse_last_pos = mouse_pos
            self.mouse_buffer.set_point(
                int(round(rel_x)),
                int(round(rel_y))
            )
            # logger.debug(f"relative mode X={rel_x}, Y={rel_y}")
            self.statusBar().showMessage(self.tr(f"Press Ctrl+Alt+F12 to release mouse"))
            if (
                    abs(mouse_pos.x() - middle_pos.x()) > 25
                    or abs(mouse_pos.y() - middle_pos.y()) > 25
            ):
                QCursor.setPos(middle_pos)
                self.mouse_last_pos = middle_pos
        else:
            self.mouse_last_pos = middle_pos
            self.mouse_buffer.clear_point()
            QCursor.setPos(middle_pos)

    # 更新鼠标坐标缓冲区
    def update_mouse_position(self, x: int, y: int):
        if not self.status["mouse_relative_mode"]:
            self.update_mouse_absolute_position(x, y)
        else:
            self.update_mouse_relative_position(x, y)
        self.mouse_need_report = True

    @staticmethod
    def convert_to_button_code(value: Qt.MouseButton) -> MouseButtonCodeEnum:
        if value == Qt.LeftButton:
            return MouseButtonCodeEnum.LEFT_BUTTON
        elif value == Qt.RightButton:
            return MouseButtonCodeEnum.RIGHT_BUTTON
        elif value == Qt.MiddleButton:
            return MouseButtonCodeEnum.MIDDLE_BUTTON
        elif value == Qt.XButton1:
            return MouseButtonCodeEnum.XBUTTON1_BUTTON
        elif value == Qt.XButton2:
            return MouseButtonCodeEnum.XBUTTON2_BUTTON
        else:
            return MouseButtonCodeEnum.UNKNOWN_BUTTON

    # 滚轮事件
    def mouse_scroll_report(self):
        if self.status["mouse_relative_mode"]:
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.controller_event_worker.command_send_signal.emit(command, self.mouse_buffer.dup())
        self.mouse_buffer.wheel = MouseWheelStateEnum.STOP

    def mouse_timer_report(self):
        if self.status["mouse_relative_mode"]:
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        if self.mouse_need_report:
            self.controller_event_worker.command_send_signal.emit(command, self.mouse_buffer.dup())
            if self.status["mouse_relative_mode"]:
                self.mouse_buffer.clear_point()
        self.mouse_need_report = False

    # 关闭事件
    def close_event(self):
        self.controller_worker_thread.quit()
        self.controller_worker_thread.wait()
        pass

    def hook_keyboard_down_event(self, event):
        logger.debug(f"Hook: {event.Key} {event.ScanCode}")
        if event.Key in self.SCANCODE_REMAP:
            scan_code = self.SCANCODE_REMAP[event.Key]
        else:
            scan_code = event.ScanCode
        if scan_code not in self.hook_pressed_keys:
            self.hook_pressed_keys.append(scan_code)
            self.update_keyboard_buffer_with_scancode(scan_code, KeyStateEnum.PRESS)
        return False

    def hook_keyboard_up_event(self, event):
        if event.Key in self.SCANCODE_REMAP:
            scan_code = self.SCANCODE_REMAP[event.Key]
        else:
            scan_code = event.ScanCode
        # self.key_release(scan_code)
        self.update_keyboard_buffer_with_scancode(scan_code, KeyStateEnum.RELEASE)
        try:
            self.hook_pressed_keys.remove(scan_code)
        except ValueError:
            pass
        return False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        p = event.position().toPoint()
        x, y = p.x(), p.y()
        # 全屏状态下检测鼠标位置
        if self.status["fullscreen_enabled"]:
            # self.fullscreen_action_timer.start(self.DEFAULT_TIMER_DELAY)
            self.fullscreen_mouse_event(x, y)
        # 非鼠标捕获的情况下显示光标
        if not self.status["mouse_captured"]:
            self.setCursor(Qt.ArrowCursor)
            return
        # 暂停鼠标的状态下不响应移动事件
        if self.status["pause_mouse"] is True:
            self.setCursor(Qt.ArrowCursor)
            return
        if self.status["hide_cursor_enabled"] or self.status["mouse_relative_mode"]:
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        self.update_mouse_position(x, y)

    # 鼠标按下事件
    def mousePressEvent(self, event: QMouseEvent):
        if (
                not self.status["mouse_captured"]
                and event.button() == Qt.LeftButton
                and self.status["camera_opened"]
        ):
            self.mouse_capture()
            return
        if self.status["mouse_captured"] is False:
            return
        if self.status["pause_mouse"] is True:
            return
        button_code = self.convert_to_button_code(event.button())
        button_state = MouseButtonStateEnum.PRESS
        if self.status["mouse_relative_mode"]:
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.mouse_buffer.set_button(button_code, button_state)
        if self.status["mouse_relative_mode"]:
            self.mouse_buffer.clear_point()
        self.controller_event_worker.command_send_signal.emit(command, self.mouse_buffer.dup())
        pass

    # 鼠标松开事件
    def mouseReleaseEvent(self, event):
        if self.status["mouse_captured"] is False:
            return
        if self.status["pause_mouse"] is True:
            return
        button_code = self.convert_to_button_code(event.button())
        button_state = MouseButtonStateEnum.RELEASE
        if self.status["mouse_relative_mode"]:
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.mouse_buffer.set_button(button_code, button_state)
        if self.status["mouse_relative_mode"]:
            self.mouse_buffer.clear_point()
        self.controller_event_worker.command_send_signal.emit(command, self.mouse_buffer.dup())

    # 鼠标滚动事件
    def wheelEvent(self, event):
        if self.status["mouse_captured"] is False:
            return
        if self.status["pause_mouse"] is True:
            return
        y = event.angleDelta().y()
        if y == 120:
            self.mouse_buffer.wheel = MouseWheelStateEnum.DOWN
        elif y == -120:
            self.mouse_buffer.wheel = MouseWheelStateEnum.UP
        else:
            self.mouse_buffer.wheel = MouseWheelStateEnum.STOP
        self.mouse_scroll_report()

    # 键盘按下事件
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return
        keyboard_modifiers = event.modifiers()
        keyboard_key = event.key()

        if keyboard_modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            is_register_function_keys: bool = True
            # Ctrl+Alt+F11 退出全屏
            if keyboard_key == Qt.Key.Key_F11:
                self.fullscreen_state_toggle()
            # Ctrl+Alt+F12 关闭鼠标捕获
            elif keyboard_key == Qt.Key.Key_F12:
                self.mouse_release()
                self.controller_device_reload("mouse")
                self.statusBar().showMessage(self.tr("Mouse capture off"))
            # Ctrl+Alt+V quick paste
            elif keyboard_key == Qt.Key.Key_V and self.status["quick_paste_enabled"]:
                self.quick_paste_trigger()
            else:
                is_register_function_keys = False
            # 如果是已注册的功能键则不传递给被控端
            if is_register_function_keys:
                self.clear_keyboard_key_buffer()
                return
        if self.status["pause_keyboard"] is True:
            return
        # 如果是指示器按键则更新指示器buffer
        if keyboard_key == Qt.Key.Key_CapsLock:
            self.update_keyboard_indicator_buffer("caps_lock")
        elif keyboard_key == Qt.Key.Key_ScrollLock:
            self.update_keyboard_indicator_buffer("scroll_lock")
        elif keyboard_key == Qt.Key.Key_NumLock:
            self.update_keyboard_indicator_buffer("num_lock")
        else:
            # 如果是非指示器按键则更新普通buffer
            self.update_keyboard_buffer_with_scancode(event.nativeScanCode(), KeyStateEnum.PRESS)
        super().keyPressEvent(event)

    # 键盘松开事件
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return
        if self.status["pause_keyboard"] is True:
            return
        self.update_keyboard_buffer_with_scancode(event.nativeScanCode(), KeyStateEnum.RELEASE)
        super().keyReleaseEvent(event)

    # 窗口改变事件
    def changeEvent(self, event):
        # 窗口失焦事件
        if event.type() == QEvent.WindowDeactivate:
            if not self.isActiveWindow() and self.status["controller_opened"]:
                # 窗口失去焦点时重置键盘，防止卡键
                self.controller_device_reload("all")
        # logger.debug(f"window change event: {event}")

    def closeEvent(self, event: QCloseEvent):
        # os._exit(0)
        self.close_event()
        super().closeEvent(event)
        pass


def clear_splash():
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(),
            "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
        )
        if os.path.exists(splash_filename):
            os.unlink(splash_filename)


def debug_mode(mode: bool):
    # 移除logger handler
    logger.remove()
    if mode is True:
        logger.add(
            sys.stdout,
            # :{function}:{line}
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {name} - {message}",
            level="DEBUG",
        )
        controller_device.ControllerDebugOptions.DEVICE = True
        controller_device.ControllerDebugOptions.MOUSE = True
        controller_device.ControllerDebugOptions.KEYBOARD = True
    else:
        logger.add(
            sys.stdout,
            # :{function}:{line}
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {name} - {message}",
            level="INFO",
        )


def command_line_parser():
    parser = argparse.ArgumentParser(description="USB KVM Client")
    parser.add_argument("-d", "--debug", action="store_true",
                        default=False,
                        help="Debug mode (default: disable)")

    args = parser.parse_args()
    debug_mode(args.debug)


def os_init():
    system_name = platform.system().lower()
    if system_name == "windows":  # sys.platform == "win32":
        app_id = "open_source_software.usb_kvm_client.gui.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        # 4K分辨率下字体发虚
        # 设置环境变量让渲染使用 freetype
        os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"
    elif system_name == "linux":
        pass
    else:
        pass


def main():
    os_init()
    command_line_parser()
    argv = sys.argv
    app = QApplication(argv)
    locale = QLocale().system().name().lower()
    translation_files: list[str] = []
    if locale == "zh_cn":
        translation_files.append(project_path.project_source_directory_path("translate", "qtbase_zh_cn.qm"))
        translation_files.append(project_path.project_source_directory_path("translate", "trans_zh_cn.qm"))
    for file_path in translation_files:
        translator = QTranslator(app)
        if translator.load(file_path):
            app.installTranslator(translator)
    my_window = MyMainWindow()
    my_window.show()
    # QTimer.singleShot(100, my_window.shortcut_status)
    clear_splash()
    return app.exec()


if __name__ == "__main__":
    exit_code: int = main()
    exit(exit_code)
