from __future__ import annotations
import typing
from PySide6.QtGui import QAction

import os
from PySide6.QtGui import QIcon, QPixmap


class IconManager:
    """图标加载服务（无状态，不再持有 action/dialog 引用）"""

    def __init__(self, source_directory: str):
        self.source_directory = source_directory

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

    def init_window_icon(
        self, set_window_icon: typing.Callable[[QIcon], None]
    ) -> None:
        main_icon: QIcon = self.load_icon("main.ico")
        set_window_icon(main_icon)

    def init_menu_icon(
        self, icon_actions: typing.Sequence[typing.Tuple[QAction, str]]
    ) -> None:
        """为菜单动作设置图标（动作与图标的对应关系由组合根注入）"""
        for action, file_name in icon_actions:
            action.setIcon(self.load_icon(file_name))
