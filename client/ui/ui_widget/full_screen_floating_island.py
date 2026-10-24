import typing

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QToolButton,
    QMenu,
)
from loguru import logger

from project_path import project_source_directory_path
from ui.standard_widget.floating_island import FloatingIsland


class FullScreenFloatingIsland(FloatingIsland):

    def __init__(self, parent: QWidget | None = None) -> None:
        self.icon_pin = QIcon(
            project_source_directory_path("icons/simple_style/island-pin.png")
        )
        self.icon_pin_off = QIcon(
            project_source_directory_path(
                "icons/simple_style/island-pin-off.png"
            )
        )
        self.icon_menu = QIcon(
            project_source_directory_path("icons/simple_style/island-menu.png")
        )
        super().__init__(parent)
        self.popup_menu = QMenu(self)

    def init_widgets(self) -> None:
        # Pin 固定按钮
        pin_button = QToolButton(self)
        pin_button.setIcon(self.icon_pin_off)
        pin_button.setIconSize(QSize(24, 24))
        pin_button.setAutoRaise(True)
        pin_button.setCheckable(True)
        pin_button.clicked.connect(self.toggle_pin)
        self.panel_layout.addWidget(pin_button, 1)
        self.add_internal_widget("pin_button", pin_button)

        # 状态提示标签
        label = QLabel(self.tr("Console"), self)
        label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent;"
        )
        # 设置上下左右完全居中
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.panel_layout.addWidget(label, 2)
        self.add_internal_widget("label", label)

        # 示例操作按钮
        menu_button = QToolButton(self)
        menu_button.setIcon(self.icon_menu)
        menu_button.setIconSize(QSize(24, 24))
        menu_button.setAutoRaise(True)
        menu_button.clicked.connect(
            lambda: logger.debug("Island menu button clicked.")
        )
        menu_button.clicked.connect(
            lambda: self.popup_menu.exec(QCursor().pos())
        )
        self.panel_layout.addWidget(menu_button, 1)
        self.add_internal_widget("menu_button", menu_button)

    def toggle_pin(self, checked: bool) -> None:
        """切换 Pin 状态"""
        super().toggle_pin(checked)
        pin_button: QToolButton = typing.cast(
            QToolButton, self.internal_widgets["pin_button"]
        )
        if self.is_pinned:
            pin_button.setIcon(self.icon_pin)
        else:
            pin_button.setIcon(self.icon_pin_off)
        pass


def example_main() -> None:
    app = QApplication()

    island = FullScreenFloatingIsland()
    island.close_requested.connect(app.quit)
    island.show()

    app.exec()


if __name__ == "__main__":
    example_main()
    pass
