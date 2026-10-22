import typing

from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QCursor, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QMenu,
)
from loguru import logger

from project_path import project_source_directory_path
from ui.standard_widget.floating_island import FloatingIsland


class FullScreenFloatingIsland(FloatingIsland):
    island_close_signal = Signal()

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
        # 按钮和标签布局
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(12, 4, 12, 4)

        # Pin 固定按钮
        pin_button = QToolButton(self.container)
        pin_button.setIcon(self.icon_pin_off)
        pin_button.setIconSize(QSize(24, 24))
        pin_button.setAutoRaise(True)
        pin_button.setCheckable(True)
        pin_button.clicked.connect(self.toggle_pin)
        layout.addWidget(pin_button, 1)
        self.internal_widgets["pin_button"] = pin_button

        # 状态提示标签
        label = QLabel(self.tr("Console"), self.container)
        label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent;"
        )
        # 设置上下左右完全居中
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 2)
        self.internal_widgets["label"] = label

        # 示例操作按钮
        menu_button = QToolButton(self.container)
        menu_button.setIcon(self.icon_menu)
        menu_button.setIconSize(QSize(24, 24))
        menu_button.setAutoRaise(True)
        menu_button.clicked.connect(
            lambda: logger.debug("Island menu button clicked.")
        )
        menu_button.clicked.connect(
            lambda: self.popup_menu.exec(QCursor().pos())
        )
        layout.addWidget(menu_button, 1)
        self.internal_widgets["menu_button"] = menu_button

        # 统一圆角样式 (8px)
        self.setStyleSheet("""
            QWidget#IslandContainer {
                background-color: #1e88e5;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 40);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 80);
            }
            QPushButton:checked {
                background-color: #0d47a1;
            }
        """)

    def toggle_pin(self, checked: bool) -> None:
        """切换 Pin 状态"""
        pin_button: QToolButton = typing.cast(
            QToolButton, self.internal_widgets["pin_button"]
        )
        self.is_pinned = checked
        if self.is_pinned:
            # self.pin_btn.setText("Pinned")
            pin_button.setIcon(self.icon_pin)
            self.collapse_delay_timer.stop()
            self.expand_island()
        else:
            pin_button.setIcon(self.icon_pin_off)
            pass

    # 重写关闭事件
    def closeEvent(self, event: QCloseEvent):
        logger.debug("Island close event triggered.")
        # 发射信号通知父窗口
        self.island_close_signal.emit()
        # 接受关闭事件
        event.accept()


def example_main() -> None:
    app = QApplication()

    island = FullScreenFloatingIsland()
    island.show()

    app.exec()


if __name__ == "__main__":
    example_main()
    pass
