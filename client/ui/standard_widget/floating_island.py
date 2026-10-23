import sys
from typing import Optional

from PySide6.QtCore import (
    Qt,
    QPoint,
    QRect,
    QPropertyAnimation,
    QTimer,
)
from PySide6.QtGui import QMouseEvent, QAction
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QMenu,
)


class FloatingIsland(QWidget):
    TRIGGER_TOP_MARGIN: int = 5

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # 窗口标志
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 状态变量初始化
        self.is_pinned: bool = False
        self.is_dragging: bool = False
        self.is_expanded: bool = True
        self.drag_position: QPoint = QPoint()

        # 尺寸定义
        self.island_width: int = 240
        self.expanded_height: int = 40
        self.collapsed_height: int = (
            0  # 0 表示完全隐藏，非 0（如 16）表示保留局部小岛
        )

        # 获取屏幕几何尺寸
        self.screen_geometry = QApplication.primaryScreen().availableGeometry()
        start_x: int = (
            self.screen_geometry.x()
            + (self.screen_geometry.width() - self.island_width) // 2
        )
        self.current_x: int = start_x

        # 初始几何区域与矩形初始化
        self.expanded_rect: QRect = QRect()
        self.collapsed_rect: QRect = QRect()
        self.update_rects()
        self.setGeometry(self.expanded_rect)

        # 外层主布局（承载内部容器）
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 内部容器 Widget（负责蓝色背景和圆角）
        self.container = QWidget(self)
        self.container.setObjectName("IslandContainer")
        self.main_layout.addWidget(self.container)

        self.internal_widgets: dict[str, QWidget] = {}
        self.init_widgets()

        # 动画对象：直接对窗口 geometry 进行丝滑动画
        self.animation: QPropertyAnimation = QPropertyAnimation(
            self, b"geometry"
        )
        self.animation.setDuration(200)
        self.animation.finished.connect(self.on_animation_finished)

        # 定时监测鼠标位置
        self.check_timer: QTimer = QTimer(self)
        self.check_timer.setInterval(100)
        self.check_timer.timeout.connect(self.check_mouse_position)
        self.check_timer.start()

        # 延迟缩回定时器 (1.5 秒)
        self.collapse_delay_timer: QTimer = QTimer(self)
        self.collapse_delay_timer.setSingleShot(True)
        self.collapse_delay_timer.setInterval(1500)
        self.collapse_delay_timer.timeout.connect(self.perform_collapse)

    def init_widgets(self) -> None:
        pass

    def update_rects(self) -> None:
        """更新展开与收缩的目标矩形"""
        self.expanded_rect = QRect(
            self.current_x, 0, self.island_width, self.expanded_height
        )
        if self.collapsed_height == 0:
            # 完全隐藏模式下，收缩高度设为 1，动画结束后再隐藏窗口
            self.collapsed_rect = QRect(self.current_x, 0, self.island_width, 1)
        else:
            self.collapsed_rect = QRect(
                self.current_x, 0, self.island_width, self.collapsed_height
            )

    def toggle_pin(self, checked: bool) -> None:
        self.is_pinned = checked
        if self.is_pinned:
            self.collapse_delay_timer.stop()
            self.expand_island()

    def check_mouse_position(self) -> None:
        # 有菜单弹出或处于钉住/拖动状态时，不进行收缩检测
        if (
            QApplication.activePopupWidget() is not None
            or self.is_pinned
            or self.is_dragging
        ):
            return

        global_pos = self.cursor().pos()
        is_hovering_island: bool = (
            self.isVisible() and self.geometry().contains(global_pos)
        )

        should_expand: bool
        if self.collapsed_height == 0:
            is_at_screen_top: bool = global_pos.y() < self.TRIGGER_TOP_MARGIN
            should_expand = is_at_screen_top or is_hovering_island
        else:
            is_at_island_top: bool = (
                global_pos.y() <= self.collapsed_height
                and self.current_x
                <= global_pos.x()
                <= self.current_x + self.island_width
            )
            should_expand = is_at_island_top or is_hovering_island

        if should_expand:
            self.collapse_delay_timer.stop()
            self.expand_island()
        else:
            if (
                self.isVisible()
                and self.is_expanded
                and not self.collapse_delay_timer.isActive()
            ):
                self.collapse_delay_timer.start()

    def perform_collapse(self) -> None:
        if QApplication.activePopupWidget() is not None:
            return

        global_pos = self.cursor().pos()
        if not self.is_pinned and not self.geometry().contains(global_pos):
            if (
                self.collapsed_height == 0
                and global_pos.y() < self.TRIGGER_TOP_MARGIN
                and self.current_x
                <= global_pos.x()
                <= self.current_x + self.island_width
            ):
                return
            self.collapse_island()

    def expand_island(self) -> None:
        if self.is_expanded and self.isVisible():
            return
        self.is_expanded = True
        self.update_rects()

        if not self.isVisible():
            super().show()

        # 展开前先显示内部控件，让布局管理器参与尺寸恢复
        self.show_internal_widgets()
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.expanded_rect)
        self.animation.start()

    def collapse_island(self) -> None:
        if not self.is_expanded:
            return
        self.is_expanded = False
        self.update_rects()

        if (
            not self.geometry().contains(self.cursor().pos())
            and not self.is_dragging
        ):
            # 收缩开始时立即隐藏内部控件，解除布局对最小高度的限制
            self.hide_internal_widgets()

            self.animation.stop()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.collapsed_rect)
            self.animation.start()

    def on_animation_finished(self) -> None:
        """动画播放完毕后的精细化状态处理"""
        if not self.is_expanded:
            if self.collapsed_height == 0:
                super().hide()

    def hide_internal_widgets(self) -> None:
        for w in self.internal_widgets.values():
            w.hide()

    def show_internal_widgets(self) -> None:
        for w in self.internal_widgets.values():
            w.show()

    def hide(self) -> None:
        self.is_expanded = False
        self.check_timer.stop()
        self.collapse_delay_timer.stop()
        super().hide()

    def show(self) -> None:
        super().show()
        self.is_expanded = True
        self.update_rects()
        if not self.is_pinned:
            self.check_timer.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.check_timer.stop()
            self.collapse_delay_timer.stop()
            self.expand_island()
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_top_left = event.globalPosition().toPoint() - self.drag_position
            target_x: int = new_top_left.x()

            min_x: int = self.screen_geometry.left()
            max_x: int = self.screen_geometry.right() - self.island_width
            self.current_x = max(min_x, min(target_x, max_x))

            self.update_rects()
            self.move(self.current_x, self.y())
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.current_x = self.x()
            self.update_rects()
            if not self.is_pinned:
                self.check_timer.start()
            event.accept()


class ExampleFloatingIsland(FloatingIsland):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        self.pin_btn: QPushButton
        self.label: QLabel
        self.action_btn: QPushButton

        super().__init__(parent)

    def init_widgets(self) -> None:
        # 使用布局管理内部控件
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(12, 4, 12, 4)

        # Pin 固定按钮
        self.pin_btn = QPushButton("Pin", self.container)
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self.toggle_pin)
        layout.addWidget(self.pin_btn)
        self.internal_widgets["pin_btn"] = self.pin_btn

        # 状态提示标签
        self.label = QLabel("Island", self.container)
        self.label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent;"
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.internal_widgets["label"] = self.label

        # 示例操作按钮（带 QMenu 菜单测试）
        self.action_btn = QPushButton("Menu", self.container)
        menu = QMenu(self.action_btn)
        menu.addAction(QAction("Option 1", menu))
        menu.addAction(QAction("Option 2", menu))
        self.action_btn.setMenu(menu)
        layout.addWidget(self.action_btn)
        self.internal_widgets["action_menu"] = self.action_btn

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
        self.is_pinned = checked
        if self.is_pinned:
            self.collapse_delay_timer.stop()
            self.expand_island()
        else:
            pass


def example_main() -> None:
    app = QApplication(sys.argv)

    island = ExampleFloatingIsland()
    # 测试非 0 的局部保留高度
    # island.collapsed_height = 5
    island.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    example_main()
