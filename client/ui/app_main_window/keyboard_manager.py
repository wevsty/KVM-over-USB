from __future__ import annotations
from loguru import logger
import typing
from .app_context import ApplicationContext
from .controller_manager import ControllerManager
from .keyboard_code_data import KeyboardCodeData
from .status_bar_manager import MainWindowStatusBarManager
from PySide6.QtGui import QKeyEvent
from ui.ui_custom_key import CustomKeyDialog
from ui.ui_indicator_lights import IndicatorLightsDialog

# 特定系统依赖
import platform

if platform.system() == "Windows":
    import keyboard_hook

import project_var
from PySide6.QtWidgets import QApplication
from data.keyboard_shift_symbol import SHIFT_SYMBOL
from keyboard_buffer import (
    KeyboardIndicatorBuffer,
    KeyboardKeyBuffer,
    KeyStateEnum,
)

from data.keyboard_text_to_hid_code import TEXT_TO_HID_CODE


class KeyboardManager:
    """键盘管理：模拟/缓冲区/事件/钩子/指示灯"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        controller_manager: ControllerManager,
        status_bar_manager: MainWindowStatusBarManager,
        keyboard_code_data: KeyboardCodeData,
        custom_key_dialog: CustomKeyDialog,
        indicator_lights_dialog: IndicatorLightsDialog,
    ):
        # 依赖由组合根注入；tr/config_manager/窗口能力经 context 共享，
        # 不再持有主窗口引用或接收冗余构造参数
        self._context = context
        self.config = context.config
        self.status = context.status
        self.timer = context.timer
        self.controller_manager = controller_manager
        self.status_bar_manager = status_bar_manager
        self.keyboard_code_data = keyboard_code_data
        self.custom_key_dialog = custom_key_dialog
        self.indicator_lights_dialog = indicator_lights_dialog
        self.tr = context.tr
        self.isActiveWindow = context.window_service.is_active_window
        self.config_manager = context.config_manager
        self.show_critical = context.window_service.show_critical
        # 键盘钩子（由 Manager 自己持有）
        self.hook_manager: typing.Any = None
        self.hook_pressed_keys: list[typing.Any] = []
        # 键盘缓冲区（由 Manager own）
        self.keyboard_key_buffer: KeyboardKeyBuffer = KeyboardKeyBuffer()
        self.keyboard_indicator_buffer: KeyboardIndicatorBuffer = (
            KeyboardIndicatorBuffer()
        )
        # 自身热键动作（Ctrl+Alt+F11/F12 等）通过消息总线广播，不再持有
        # WindowManager 引用；快捷键菜单刷新同理（见 custom_key_save）
        self.hotkey_action_triggered = (
            self._context.event_bus.hotkey_action_triggered.emit
        )
        # 跨 Manager 命令/数据经消息总线（解耦 ControllerManager ↔ KeyboardManager）
        self._context.event_bus.clear_keyboard_buffer.connect(
            self.clear_keyboard_buffer
        )
        self._context.event_bus.keyboard_data_received.connect(
            self.on_keyboard_data_received
        )

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
        self.controller_manager.controller_sleep_ms(1)
        for key_code in key_code_list:
            self.update_keyboard_buffer_with_hid_code(
                key_code, KeyStateEnum.RELEASE
            )
            self.send_keyboard_buffer()

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
        self.config_manager.save_config()
        # 通知菜单重建快捷键子菜单（经消息总线，解耦 keyboard→menu）
        self._context.event_bus.shortcut_keys_changed.emit()

    def shortcut_key_triggered(self, action_name: str):
        for keys_name in self.config.shortcut_keys:
            if action_name == keys_name:
                send_buffer = self.config.shortcut_keys[action_name]
                self.shortcut_key_send(send_buffer)
                break
            pass
        pass

    def disable_hotkey_triggered(self):
        self.status.reverse_bool("disable_hotkey")

    def user_input_block(self, block: bool):
        self.status.set_bool("block_input", block)

    def keyboard_simulation_press(self, hid_code: int):
        # 更新键盘buffer
        self.update_keyboard_buffer_with_hid_code(hid_code, KeyStateEnum.PRESS)
        self.send_keyboard_buffer()

    def keyboard_simulation_release(self, hid_code: int):
        # 更新键盘buffer
        self.update_keyboard_buffer_with_hid_code(
            hid_code, KeyStateEnum.RELEASE
        )
        self.send_keyboard_buffer()

    def keyboard_simulation_click(self, hid_code: int):
        # 指示器按键则更新指示器buffer
        self.update_keyboard_indicator_buffer_with_hid_code(hid_code)
        self.keyboard_simulation_press(hid_code)
        self.keyboard_simulation_release(hid_code)

    def keyboard_simulation_click_with_keyname(self, data: str):
        result, hid_code = self.keyboard_code_data.convert_key_name_to_hid_code(
            data
        )
        if not result:
            return
        self.keyboard_simulation_click(hid_code)

    def keyboard_send_string(self, data: str):
        self.user_input_block(True)
        # 获取必要的 hid code
        status, shift_hid_code = (
            self.keyboard_code_data.convert_key_name_to_hid_code("shift")
        )
        assert status is not False
        status, caps_lock_hid_code = (
            self.keyboard_code_data.convert_key_name_to_hid_code("caps_lock")
        )
        assert status is not False
        # 强制关闭 capslock
        if self.keyboard_indicator_buffer.caps_lock:
            self.keyboard_simulation_click(caps_lock_hid_code)

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
                self.keyboard_simulation_press(shift_hid_code)
                self.keyboard_simulation_press(key_code)
                self.keyboard_simulation_release(shift_hid_code)
                self.keyboard_simulation_release(key_code)
            else:
                self.keyboard_simulation_press(key_code)
                self.keyboard_simulation_release(key_code)
            self.controller_manager.controller_sleep_ms(
                self.config.paste_board["interval"]
            )

        # 再次强制清空缓冲区
        self.clear_keyboard_buffer()
        self.send_keyboard_buffer()

        self.user_input_block(False)

    def quick_paste_toggle(self):
        self.status.reverse_bool("quick_paste")
        quick_paste = self.status.get_bool("quick_paste")
        self.status_bar_manager.show_message(
            self.tr("Quick paste: ")
            + self.config_manager.to_enabled_string(quick_paste)
        )

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

    def sync_indicator_triggered(self):
        self.sync_keyboard_indicator_to_buffer()

    def sync_keyboard_indicator_to_buffer(self):
        self.keyboard_indicator_buffer.clear()
        self.controller_manager.controller_command_send("keyboard_read", None)

    def execute_indicator_lights_dialog(self):
        if self.indicator_lights_dialog.isVisible():
            self.indicator_lights_dialog.activateWindow()
            return
        self._context.event_bus.move_dialog_to_center.emit(
            self.indicator_lights_dialog
        )
        self.indicator_lights_dialog.update_buffer(
            self.keyboard_indicator_buffer
        )
        self.indicator_lights_dialog.refresh_status_from_buffer()
        self.indicator_lights_dialog.exec()

    def init_system_hook(self):
        if platform.system() == "Windows":
            pass
        else:
            return
        self.hook_manager = keyboard_hook.KeyboardHookManager()
        self.hook_manager.handler_key_down = self.hook_keyboard_down_event
        self.hook_manager.handler_key_up = self.hook_keyboard_up_event
        hook_pump_timer = self.timer.create("HOOK_PUMP_TIMER")
        hook_pump_timer.timeout.connect(keyboard_hook.pump_waiting_messages)
        # 定时检查钩子安装状态与窗口激活状态是否一致
        hook_state_timer = self.timer.create("HOOK_STATE_TIMER")
        hook_state_timer.timeout.connect(self.sync_system_hook_state)
        hook_state_timer.start(1000)

    def system_hook_triggered(self):
        system_name = platform.system()
        if system_name == "Windows":
            pass
        else:
            self.show_critical(
                self.tr("Error"),
                self.tr("System hook only support windows."),
            )
            return
        self.status.reverse_bool("hook_state")
        hook_state = self.status.get_bool("hook_state")
        self.status_bar_manager.show_message(
            self.tr("System hook: ")
            + self.config_manager.to_enabled_string(hook_state)
        )
        self.sync_system_hook_state()

    def sync_system_hook_state(self) -> None:
        if platform.system() != "Windows":
            return
        hook_pump_timer = self.timer.get_exists("HOOK_PUMP_TIMER")
        expected_hook_state = self.status.get_bool("hook_state")
        expected_hook_state = expected_hook_state and self.isActiveWindow()
        hooked = self.hook_manager.is_hooked()
        if expected_hook_state and not hooked:
            hook_pump_timer.start(10)
            self.hook_manager.hook_keyboard()
        elif not expected_hook_state and hooked:
            hook_pump_timer.stop()
            self.hook_manager.unhook_keyboard()
        else:
            pass

    def hook_keyboard_down_event(
        self, event: keyboard_hook.HookKeyboardEvent
    ) -> bool:
        logger.debug(
            f"keyboard hook: vk({hex(event.vk_code)}) scan_code({hex(event.scan_code)})"
        )
        self.handle_key_press_with_hid_code(event.hid_code)
        if event.hid_code not in self.hook_pressed_keys:
            self.hook_pressed_keys.append(event.hid_code)
        return False

    def hook_keyboard_up_event(
        self, event: keyboard_hook.HookKeyboardEvent
    ) -> bool:
        self.handle_key_release_with_hid_code(event.hid_code)
        try:
            self.hook_pressed_keys.remove(event.hid_code)
        except ValueError:
            pass
        return False

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

        # Ctrl+Alt+F10 关闭系统钩子(安全退出, 恢复本地键盘)
        _, f10 = self.keyboard_code_data.convert_key_name_to_hid_code("f10")
        if self.status.is_enabled(
            "hook_state"
        ) and self.keyboard_key_buffer.is_pressed(f10):
            self.system_hook_triggered()
            handle_status = True

        # Ctrl+Alt+F11 退出全屏（通过事件通知 WindowManager）
        _, f11 = self.keyboard_code_data.convert_key_name_to_hid_code("f11")
        if self.status.is_enabled(
            "fullscreen"
        ) and self.keyboard_key_buffer.is_pressed(f11):
            self.hotkey_action_triggered("toggle_fullscreen")
            handle_status = True

        # Ctrl+Alt+F12 关闭鼠标捕获（通过事件通知）
        _, f12 = self.keyboard_code_data.convert_key_name_to_hid_code("f12")
        if self.status.is_enabled(
            "mouse_capture"
        ) and self.keyboard_key_buffer.is_pressed(f12):
            self.hotkey_action_triggered("release_mouse_capture")
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

    def send_keyboard_buffer(self):
        if project_var.debug_mode:
            logger.debug(f"keyboard send: {str(self.keyboard_key_buffer)}")
        self.controller_manager.controller_command_send(
            "keyboard_write", self.keyboard_key_buffer.dup()
        )
        self.status_bar_manager.update_label_status(
            self.keyboard_key_buffer, self.keyboard_indicator_buffer
        )
        # 从缓冲区中清理已松开的按键
        self.keyboard_key_buffer.clear_released()
        # 控制器固定等待至少 1ms 确保系统能正确的响应按键信号
        self.controller_manager.controller_sleep_ms(1)

    def clear_keyboard_buffer(self):
        self.keyboard_key_buffer.clear()
        self.controller_manager.controller_command_send(
            "keyboard_write", self.keyboard_key_buffer.dup()
        )

    def on_keyboard_data_received(self, data: typing.Any) -> None:
        self.keyboard_indicator_buffer.from_dict(data)
        self.status_bar_manager.update_label_status(
            self.keyboard_key_buffer, self.keyboard_indicator_buffer
        )

    def update_keyboard_buffer_with_hid_code(
        self, hid_code: int, state: KeyStateEnum
    ) -> None:
        if state == KeyStateEnum.PRESS:
            self.keyboard_key_buffer.key_press(hid_code)
        else:
            self.keyboard_key_buffer.key_release(hid_code)

    def update_keyboard_buffer(
        self, hid_code: int, state: KeyStateEnum
    ) -> None:
        self.update_keyboard_buffer_with_hid_code(hid_code, state)

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
