from __future__ import annotations
from loguru import logger
import project_var
import typing
from .app_context import ApplicationContext
from .controller_manager import ControllerManager
from .status_bar_manager import MainWindowStatusBarManager
from PySide6.QtGui import QMouseEvent, QWheelEvent

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor
from mouse_buffer import (
    MouseButtonCodeEnum,
    MouseButtonStateEnum,
    MouseStateBuffer,
    MouseWheelStateEnum,
)


class MouseManager:
    """鼠标管理：捕获/释放/模式/光标/事件"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        controller_manager: ControllerManager,
        status_bar_manager: MainWindowStatusBarManager,
        video_manager: "VideoManager | None" = None,
    ):
        # 依赖由组合根注入；tr/config_manager 经 context 共享，
        # 窗口几何经 context.status、坐标转换经 context.window_service 获取，
        # 不再持有主窗口引用或接收冗余构造参数
        self._context = context
        self.config = context.config
        self.status = context.status
        self.timer = context.timer
        self.controller_manager = controller_manager
        self.status_bar_manager = status_bar_manager
        self.video_manager = video_manager
        self.tr = context.tr
        self.config_manager = context.config_manager
        self.mapToGlobal = context.window_service.map_to_global
        self.setCursor = context.window_service.set_cursor
        # 窗口尺寸从 StatusBuffer 读取（由门面在 resize 事件写回），
        # 并订阅变更以缓存，避免每次鼠标事件都查 StatusBuffer
        size = context.window_service.size()
        self._window_width = size.width()
        self._window_height = size.height()
        self._context.event_bus.on_status(
            "window_width", self._update_window_width
        )
        self._context.event_bus.on_status(
            "window_height", self._update_window_height
        )
        # 鼠标缓冲区（由 Manager own）
        self.mouse_buffer: MouseStateBuffer = MouseStateBuffer()
        self.mouse_last_pos: None | QPoint = None
        self.mouse_relative_speed: int = 100
        self.mouse_report_interval: int = 20
        self.mouse_report_at_next: bool = False
        self.fullscreen_event_command: str = "unknown"
        # 跨 Manager 命令经消息总线（解耦 ControllerManager ↔ MouseManager）
        self._context.event_bus.mouse_capture_triggered.connect(
            self.mouse_capture_triggered
        )
        self._context.event_bus.clear_mouse_buffer.connect(
            self.clear_mouse_buffer
        )

    def _update_window_width(self, value: int) -> None:
        self._window_width = value

    def _update_window_height(self, value: int) -> None:
        self._window_height = value

    def mouse_capture_triggered(self) -> None:
        self.status.set_bool("mouse_capture", True)
        self.status_bar_manager.show_message(
            self.tr("Mouse capture on (Press Ctrl+Alt+F12 to release)")
        )

    def mouse_capture_release_triggered(self) -> None:
        self.status.set_bool("mouse_capture", False)
        self.status_bar_manager.show_message(self.tr("Mouse released"))

    def mouse_relative_mode_triggered(self):
        self.status.reverse_bool("relative_mode")
        relative_mode = self.status.get_bool("relative_mode")
        self.status_bar_manager.show_message(
            self.tr("Relative mouse: ")
            + self.config_manager.to_enabled_string(relative_mode)
        )

    def mouse_hide_cursor_triggered(self) -> None:
        self.status.reverse_bool("hide_cursor")
        hide_cursor = self.status.get_bool("hide_cursor")
        self.status_bar_manager.show_message(
            self.tr("Hide cursor when capture mouse: ")
            + self.config_manager.to_enabled_string(hide_cursor)
        )

    def mouse_cursor_correction_triggered(self) -> None:
        self.status.reverse_bool("correction_cursor")
        correction_cursor = self.status.get_bool("correction_cursor")
        self.status_bar_manager.show_message(
            self.tr("Correction cursor: ")
            + self.config_manager.to_enabled_string(correction_cursor)
        )

    def update_mouse_report_frequency(self, frame_rate: int = 60):
        if self.config.mouse["report_frequency"] != 0:
            self.mouse_report_interval = (
                1000 / self.config.mouse["report_frequency"]
            )
        else:
            self.mouse_report_interval = 1000 / frame_rate
        self.mouse_report_interval = int(self.mouse_report_interval)
        mouse_report_timer = self.timer.get("MOUSE_REPORT_TIMER")
        assert mouse_report_timer is not None
        if mouse_report_timer is not None:
            mouse_report_timer.setInterval(self.mouse_report_interval)

    def mouse_report_scroll(self):
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        self.controller_manager.controller_command_send(
            command, self.mouse_buffer.dup()
        )
        self.mouse_buffer.wheel = MouseWheelStateEnum.STOP

    def mouse_report_timer_triggered(self):
        if self.status.is_enabled("relative_mode"):
            command = "mouse_relative_write"
        else:
            command = "mouse_absolute_write"
        if self.mouse_report_at_next:
            self.controller_manager.controller_command_send(
                command, self.mouse_buffer.dup()
            )
            if self.status.is_enabled("relative_mode"):
                self.mouse_buffer.clear_point()
        self.mouse_report_at_next = False

    def update_mouse_position_buffer(self, x: int, y: int):
        if not self.status.is_enabled("relative_mode"):
            self.update_mouse_position_buffer_with_absolute_mode(x, y)
        else:
            self.update_mouse_position_buffer_with_relative_mode()
        self.mouse_report_at_next = True

    def update_mouse_position_buffer_with_absolute_mode(self, x: int, y: int):
        self.mouse_last_pos = None
        # 视频区域几何信息委托给视频设备管理器（避免直接引用 video_widget）
        (
            x_res,
            y_res,
            width,
            height,
            x_pos,
            y_pos,
        ) = self.video_manager.get_mouse_mapping_geometry()
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

    def update_mouse_position_buffer_with_relative_mode(self):
        relative_mouse_speed = self.config.mouse["relative_speed"]
        middle_pos = self.mapToGlobal(
            QPoint(int(self._window_width / 2), int(self._window_height / 2))
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
                self.status.set_bool("disable_hotkey", False)
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

    @staticmethod
    def convert_to_button_code(value: Qt.MouseButton) -> MouseButtonCodeEnum:
        convert_table: dict[Qt.MouseButton, MouseButtonCodeEnum] = {
            Qt.MouseButton.LeftButton: MouseButtonCodeEnum.LEFT_BUTTON,
            Qt.MouseButton.RightButton: MouseButtonCodeEnum.RIGHT_BUTTON,
            Qt.MouseButton.MiddleButton: MouseButtonCodeEnum.MIDDLE_BUTTON,
            Qt.MouseButton.XButton1: MouseButtonCodeEnum.XBUTTON1_BUTTON,
            Qt.MouseButton.XButton2: MouseButtonCodeEnum.XBUTTON2_BUTTON,
        }
        button_code = convert_table.get(
            value, MouseButtonCodeEnum.UNKNOWN_BUTTON
        )
        return button_code

    def clear_mouse_buffer(self):
        self.mouse_buffer.clear()

    def handle_mouse_move_event(self, event: QMouseEvent) -> None:
        p = event.position().toPoint()
        x, y = p.x(), p.y()
        # 全屏状态下检测鼠标位置
        if self.status.is_enabled("fullscreen"):
            self.handle_mouse_on_fullscreen_event(x, y)
        # 非鼠标捕获的情况下显示光标
        if not self.status.is_enabled("mouse_capture"):
            self.setCursor(Qt.CursorShape.ArrowCursor)
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
            self.setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update_mouse_position_buffer(x, y)

    def handle_mouse_press_event(self, event: QMouseEvent) -> None:
        if (
            not self.status.is_enabled("mouse_capture")
            and event.button() == Qt.MouseButton.LeftButton
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
        self.controller_manager.controller_command_send(
            command, self.mouse_buffer.dup()
        )

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
        self.controller_manager.controller_command_send(
            command, self.mouse_buffer.dup()
        )
        self.mouse_buffer.clear_button()

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

    def handle_mouse_on_fullscreen_event(self, x: int, y: int):
        if not self.status.is_enabled("fullscreen"):
            return
        # 常量
        const_pixel = 5
        const_delay_ms = 1000 * 3

        width = self._window_width
        height = self._window_height
        event_timer = self.timer.get_exists("FULLSCREEN_EVENT_TIMER")

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
