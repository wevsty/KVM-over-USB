from __future__ import annotations
import typing
from loguru import logger
from .bootstrap import logger_init
from .app_context import ApplicationContext
from .controller_manager import ControllerManager
from .keyboard_manager import KeyboardManager
from .mouse_manager import MouseManager
from .status_bar_manager import MainWindowStatusBarManager
from .video_manager import VideoManager
from PySide6.QtCore import QEvent
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QDialog
from ui.ui_settings import SettingsDialog

import copy
import platform
import project_var
import shutil
import subprocess
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaRecorder


class WindowManager:
    """窗口管理：设备编排/全屏/状态/对话框/工具/事件分发"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        video_manager: VideoManager,
        controller_manager: ControllerManager,
        mouse_manager: MouseManager,
        keyboard_manager: KeyboardManager,
        status_bar_manager: MainWindowStatusBarManager,
        settings_dialog: SettingsDialog,
    ):
        # 依赖由组合根注入；窗口行为统一经 context.window_service 调用，
        # tr/config_manager 经 context 共享，不再持有主窗口引用
        self._context = context
        self.config = context.config
        self.status = context.status
        self.timer = context.timer
        self.threads = context.threads
        self.video_manager = video_manager
        self.controller_manager = controller_manager
        self.mouse_manager = mouse_manager
        self.keyboard_manager = keyboard_manager
        self.status_bar_manager = status_bar_manager
        self.settings_dialog = settings_dialog

        # 订阅消息总线：键盘热键动作交由本管理器解释执行（解耦 keyboard→window）
        self._context.event_bus.hotkey_action_triggered.connect(
            self.handle_keyboard_hotkey
        )
        # 订阅消息总线：键盘管理器请求将对话框居中（解耦 keyboard→window）
        self._context.event_bus.move_dialog_to_center.connect(
            self.move_dialog_to_center
        )

    def connect_devices(self):
        self.video_manager.connect_video_device()
        self.controller_manager.connect_controller()

    def disconnect_devices(self):
        self.video_manager.disconnect_video_device()
        self.controller_manager.disconnect_controller()

    def reload_devices(self):
        self.controller_manager.reload_controller("all")

    def reset_devices(self):
        self.controller_manager.reset_controller()

    def auto_connect_on_startup(self):
        if self.config.connection["auto_connect"]:
            self.connect_devices()

    def fullscreen_state_toggle(self) -> None:
        self.status.reverse_bool("fullscreen")
        if self.status.is_enabled("fullscreen"):
            if self.config.ui["tips_fullscreen"]:
                close_next_tip = self._context.window_service.show_optional_information(
                    self._context.tr("Tip"),
                    self._context.tr(
                        "Press Ctrl+Alt+F11 to toggle fullscreen.\n"
                    )
                    + self._context.tr(
                        "Or stay cursor at left top corner to show menu bar."
                    ),
                    self._context.tr("Don't show again."),
                )
                if (
                    close_next_tip is True
                    and self.config.ui["tips_fullscreen"] is True
                ):
                    self.config.ui["tips_fullscreen"] = False
                    self._context.config_manager.save_config()
            self._context.window_service.show_full_screen()
            self._context.window_service.status_bar().hide()
            self._context.window_service.menu_bar().hide()
        else:
            event_timer = self.timer.get_exists("FULLSCREEN_EVENT_TIMER")
            event_timer.stop()
            self._context.window_service.show_normal()
            self._context.window_service.status_bar().show()
            self._context.window_service.menu_bar().show()

    def execute_fullscreen_event_command(self):
        event_timer = self.timer.get_exists("FULLSCREEN_EVENT_TIMER")
        # fullscreen_event_command 由 MouseManager.handle_mouse_on_fullscreen_event 写入
        command = self.mouse_manager.fullscreen_event_command
        if command == "show_menu_bar":
            if self._context.window_service.menu_bar().isHidden():
                self._context.window_service.menu_bar().show()
        elif command == "show_status_bar":
            if self._context.window_service.status_bar().isHidden():
                self._context.window_service.status_bar().show()
        elif command == "hide_all":
            if not self._context.window_service.menu_bar().isHidden():
                self._context.window_service.menu_bar().hide()
            if not self._context.window_service.status_bar().isHidden():
                self._context.window_service.status_bar().hide()
        else:
            pass
        event_timer.stop()

    # 处理 KeyboardManager 自身热键触发的动作（组合根注入到 KeyboardManager）
    def handle_keyboard_hotkey(self, action: str) -> None:
        if action == "toggle_fullscreen":
            self.fullscreen_state_toggle()
        elif action == "release_mouse_capture":
            self.mouse_manager.mouse_capture_release_triggered()
            self.controller_manager.reload_controller("mouse")
            self.status_bar_manager.show_message(
                self._context.tr("Mouse capture off")
            )

    def window_topmost_state_toggle(self):
        self.status.reverse_bool("topmost_window")
        current_window_flag = self._context.window_service.window_flags()
        if self.status.is_enabled("topmost_window"):
            self._context.window_service.window_handle().setFlags(
                current_window_flag
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        else:
            self._context.window_service.window_handle().setFlags(
                current_window_flag & ~Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        self.status_bar_manager.show_message(
            self._context.tr("Window topmost: ")
            + self._context.config_manager.to_enabled_string(
                self.status.is_enabled("topmost_window")
            )
        )

    def keep_aspect_ratio_toggle(self):
        self.status.reverse_bool("keep_aspect_ratio")
        # 宽高比切换委托给视频设备管理器（避免直接引用 video_widget）
        self.video_manager.set_aspect_ratio_mode()
        self.status_bar_manager.show_message(
            self._context.tr("Keep aspect ratio: ")
            + self._context.config_manager.to_enabled_string(
                self.status["keep_aspect_ratio"]
            )
        )

    # 通过视频设备分辨率调整窗口大小（实现在 VideoManager，此处委托）
    def resize_window_with_video_resolution(self) -> None:
        self.video_manager.resize_window_with_video_resolution()

    def image_capture_done(self, capture_id: int, preview: QImage) -> None:
        logger.debug("image_capture_id: ", capture_id)
        file_name = self._context.window_service.get_save_file_name(
            self._context.tr("Image Save"),
            "untitled.png",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if file_name == "":
            return
        preview.save(file_name)
        self.status_bar_manager.show_message(
            self._context.tr("Image saved to") + f" {file_name}"
        )

    def image_capture_triggered(self) -> None:
        self.video_manager.video_session.image_capture.imageCaptured.disconnect(
            self.image_capture_done
        )
        self.video_manager.video_session.image_capture.imageCaptured.connect(
            self.image_capture_done
        )
        if self.status.is_enabled("camera"):
            self.video_manager.video_session.image_capture.capture()

    def video_record_triggered(self) -> None:
        record: QMediaRecorder = self.video_manager.video_session.video_record
        if not self.status.is_enabled("camera"):
            return

        if self.status.is_enabled("video_recording"):
            record.stop()
            self.status.set_bool("video_recording", False)
            self.status_bar_manager.show_message(
                self._context.tr("Video recording stopped")
            )
        else:
            file_name = self._context.window_service.get_save_file_name(
                self._context.tr("Video save"),
                "output.mp4",
                "Video (*.mp4)",
            )
            if file_name == "":
                return
            if (
                self.video_manager.video_session.video_record.recorderState()
                != QMediaRecorder.RecorderState.StoppedState
            ):
                record.stop()
            record.setOutputLocation(QUrl.fromLocalFile(file_name))
            record.record()
            self.status.set_bool("video_recording", True)
            self.status_bar_manager.show_message(
                self._context.tr("Video recording started")
            )

    def sync_pause_keyboard_state(self) -> None:
        self.status.reverse_bool("pause_keyboard")

    def sync_pause_mouse_state(self) -> None:
        self.status.reverse_bool("pause_mouse")

    def menu_tools_actions(self, action_name: str):
        system_name = platform.system().lower()
        if system_name == "windows":  # sys.platform == "win32":
            pass
        else:
            self._context.window_service.show_critical(
                self._context.tr("Error"),
                self._context.tr("This tool only support windows"),
            )
            return
        file_path: str | None = None
        if action_name == "devmgmt.msc":
            mmc_path = shutil.which("mmc.exe")
            msc_path = shutil.which("devmgmt.msc")
            if mmc_path is None or msc_path is None:
                file_path = None
            else:
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

    def tips_system_warning(self):
        system_name = platform.system().lower()
        if system_name == "windows":
            return
        if self.config.ui["tips_system_warning"] is False:
            return
        close_next_tip = self._context.window_service.show_optional_information(
            self._context.tr("Tip"),
            self._context.tr("The current operating system is not Windows.\n")
            + self._context.tr("Some features will be unavailable.\n"),
            self._context.tr("Don't show again."),
        )
        if (
            close_next_tip is True
            and self.config.ui["tips_system_warning"] is True
        ):
            self.config.ui["tips_system_warning"] = False
            self._context.config_manager.save_config()

    def switch_debug_mode(self):
        project_var.debug_mode = not project_var.debug_mode
        logger_init()

    def move_dialog_to_center(self, dlg: QDialog) -> None:
        # 确保窗口位置
        wm_pos = self._context.window_service.geometry()
        wm_size = self._context.window_service.size()
        dlg.move(
            int(wm_pos.x() + wm_size.width() / 2 - dlg.width() / 2),
            int(wm_pos.y() + wm_size.height() / 2 - dlg.height() / 2),
        )

    def execute_settings_dialog(self) -> None:
        # 从配置文件读取配置
        video_config: dict[str, typing.Any] = copy.copy(self.config.video)
        controller_config: dict[str, typing.Any] = copy.copy(
            self.config.controller
        )
        connection_config: dict[str, typing.Any] = copy.copy(
            self.config.connection
        )
        ui_config: dict[str, typing.Any] = copy.copy(self.config.ui)

        # 刷新设备信息
        self.settings_dialog.refresh_devices()

        # 传入配置文件的配置
        self.settings_dialog.set_video_config(video_config)
        self.settings_dialog.set_controller_config(controller_config)
        self.settings_dialog.set_connection_config(connection_config)
        self.settings_dialog.set_ui_config(ui_config)

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
                ui_config = self.settings_dialog.get_ui_config()
                # 检查选项是否有效
                if video_config["device"] == "":
                    raise ValueError("Invalid device")
                if video_config["device"] == "empty_device":
                    if self.config.ui["tips_empty_video_device"]:
                        close_next_tip = self._context.window_service.show_optional_information(
                            self._context.tr("Tip"),
                            self._context.tr(
                                "Select empty_device means that no video output will be used.\n"
                            )
                            + self._context.tr(
                                "Used only for input operations.\n"
                            ),
                            self._context.tr("Don't show again."),
                        )
                        if (
                            close_next_tip is True
                            and self.config.ui["tips_empty_video_device"]
                            is True
                        ):
                            self.config.ui["tips_empty_video_device"] = False
                            self._context.config_manager.save_config()
                # 与配置文件合并
                self.config.video.update(video_config)
                self.config.controller.update(controller_config)
                self.config.connection.update(connection_config)
                self.config.ui.update(ui_config)
                # 保存配置
                self._context.config_manager.save_config()
            except ValueError:
                self._context.window_service.show_critical(
                    self._context.tr("Video Error"),
                    self._context.tr("Invalid device selected"),
                )
            # 尝试按照新配置启动
            # 刷新界面语言
            self._context.config_manager.refresh_translate()
            pass
        pass

    def handle_change_event(self, event: QEvent) -> None:
        # 窗口失焦事件
        window_activate_event: list[QEvent.Type] = [
            QEvent.Type.ActivationChange,
            QEvent.Type.WindowActivate,
            QEvent.Type.WindowDeactivate,
        ]
        if event.type() in window_activate_event:
            is_active_window: bool = (
                self._context.window_service.is_active_window()
            )
            if not is_active_window and self.status.is_enabled("relative_mode"):
                # 如果窗口失焦自动释放鼠标捕捉
                self.mouse_manager.mouse_capture_release_triggered()
            if not is_active_window and self.status.is_enabled("controller"):
                # 窗口失去焦点时释放键盘和鼠标
                # 防止卡键
                self.controller_manager.reload_controller("all")
            # 窗口激活状态变化时同步系统钩子状态
            self.keyboard_manager.sync_system_hook_state()
            pass
        logger.debug(f"window change event: {event}")

    def handle_close_event(self) -> None:
        self.controller_manager.disconnect_controller()
        self.timer.quit_all()
        self.threads.quit_all()
