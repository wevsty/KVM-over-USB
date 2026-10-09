from __future__ import annotations
from .app_context import ApplicationContext


class MenuManager:
    """菜单管理：快捷键菜单/菜单信号连接/菜单状态"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        menu_shortcut_keys,
        custom_key_dialog,
        indicator_lights_dialog,
        keyboard_manager,
        controller_manager,
        controller_event,
    ):
        # 菜单动作/对话框/其他 Manager 由组合根注入；
        # 窗口相关行为以"实例化函数"（绑定方法）注入，不再持有主窗口引用
        self._context = context
        self.config = context.config
        self.status = context.status

        self.menu_shortcut_keys = menu_shortcut_keys

        self.custom_key_dialog = custom_key_dialog
        self.indicator_lights_dialog = indicator_lights_dialog

        self.keyboard_manager = keyboard_manager
        self.controller_manager = controller_manager

        self.controller_event = controller_event

        # 订阅消息总线：自定义快捷键保存后重建快捷键子菜单（解耦 keyboard→menu）
        self._context.event_bus.shortcut_keys_changed.connect(
            self.init_shortcut_keys_menu
        )

    def init_shortcut_keys_menu(self) -> None:
        self.menu_shortcut_keys.clear()
        for action_name in self.config.shortcut_keys.keys():
            action = self.menu_shortcut_keys.addAction(action_name)
            action.triggered.connect(
                lambda _checked, triggered_keys=action_name: self.keyboard_manager.shortcut_key_triggered(
                    triggered_keys
                )
            )
        pass

    def init_menu_checked_state(self) -> None:
        """依据配置初始化菜单相关的 StatusBuffer 状态（不再操作 QAction）"""
        if self.config.video["keep_aspect_ratio"]:
            self.status.set_bool("keep_aspect_ratio", True)
        if self.config.ui["quick_paste"]:
            self.status.set_bool("quick_paste", True)

    def init_connect_signal(self) -> None:
        # keyboard 菜单需要的信号连接
        self.indicator_lights_dialog.lock_key_clicked_signal.connect(
            self.keyboard_manager.keyboard_simulation_click_with_keyname
        )

        # controller event
        self.controller_event.command_reply_signal.connect(
            self.controller_manager.controller_command_reply
        )
        pass
