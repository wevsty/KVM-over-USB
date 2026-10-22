import sys
from typing import Optional

from PySide6.QtCore import (
    Qt,
    QPoint,
    QRect,
    QPropertyAnimation,
    QTimer,
    Property,
)
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QLabel,
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
        self.dragging: bool = False
        self.is_expanded: bool = True
        self.drag_position: QPoint = QPoint()

        # 尺寸定义
        self.island_width: int = 240
        self.expanded_height: int = 40
        self.collapsed_height: int = 0  # 0 表示完全隐藏

        # 获取屏幕几何尺寸
        self.screen_geometry = QApplication.primaryScreen().availableGeometry()
        start_x: int = (
            self.screen_geometry.x()
            + (self.screen_geometry.width() - self.island_width) // 2
        )

        self.current_x: int = start_x

        # 顶层窗口始终保持固定最大高度
        self.setGeometry(
            self.current_x, 0, self.island_width, self.expanded_height
        )

        # 外层主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建内层容器 Widget
        self.container = QWidget(self)
        self.container.setObjectName("IslandContainer")
        self.main_layout.addWidget(self.container)

        # 初始将 container 设为收起状态
        self.container.setGeometry(
            0, -self.expanded_height, self.island_width, self.expanded_height
        )

        self.internal_widgets: dict[str, QWidget] = {}
        self.init_widgets()

        # 动画对象驱动内层 container 的 geometry 属性
        self.animation: QPropertyAnimation = QPropertyAnimation(
            self, b"container_geometry"
        )
        self.animation.setDuration(200)
        # 绑定动画结束信号，用于精准控制收缩后的隐藏
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

        # 初始直接展开
        self.expand_island()

    def init_widgets(self) -> None:
        pass

    # --- Property 属性包装器 ---
    @Property(QRect)
    def container_geometry(self) -> QRect:
        if not hasattr(self, "container"):
            return QRect()
        return self.container.geometry()

    @container_geometry.setter
    def container_geometry(self, rect: QRect) -> None:
        if hasattr(self, "container"):
            self.container.setGeometry(rect)

    def toggle_pin(self, checked: bool) -> None:
        self.is_pinned = checked
        if self.is_pinned:
            self.collapse_delay_timer.stop()
            self.expand_island()

    def check_mouse_position(self) -> None:
        # 只要有菜单正在弹出显示就放弃检查
        if QApplication.activePopupWidget() is not None:
            return
        # 拖动状态或者钉住时放弃检查
        if self.is_pinned or self.dragging:
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
                global_pos.y() <= self.expanded_height
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
        # 只要有菜单正在弹出显示就放弃检查
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
        self.is_expanded = True
        if not self.isVisible():
            # 展开前先将 container 放在隐藏位置，然后显示窗口
            self.container.setGeometry(
                0,
                -self.expanded_height,
                self.island_width,
                self.expanded_height,
            )
            super().show()
            self.show_internal_widgets()

        target_rect = QRect(0, 0, self.island_width, self.expanded_height)
        if self.container.geometry() != target_rect:
            self.show_internal_widgets()
            self.animation.stop()
            self.animation.setStartValue(self.container.geometry())
            self.animation.setEndValue(target_rect)
            self.animation.start()

    def collapse_island(self) -> None:
        self.is_expanded = False

        if (
            not self.geometry().contains(self.cursor().pos())
            and not self.dragging
        ):
            target_rect = QRect(
                0,
                -self.expanded_height,
                self.island_width,
                self.expanded_height,
            )
            if self.container.geometry() != target_rect:
                self.animation.stop()
                self.animation.setStartValue(self.container.geometry())
                self.animation.setEndValue(target_rect)
                self.animation.start()

    def on_animation_finished(self) -> None:
        """动画播放完毕后的精细化状态处理"""
        if not self.is_expanded:
            # 如果是收缩动画结束，且为 0 高度模式，则立即无缝隐藏顶层窗口，彻底消除残影
            if self.collapsed_height == 0:
                super().hide()
            self.hide_internal_widgets()

    def hide_internal_widgets(self) -> None:
        for _name, widget_object in self.internal_widgets.items():
            widget_object.hide()

    def show_internal_widgets(self) -> None:
        for _name, widget_object in self.internal_widgets.items():
            widget_object.show()

    def hide(self) -> None:
        self.is_expanded = False
        self.check_timer.stop()
        self.collapse_delay_timer.stop()
        super().hide()

    def show(self) -> None:
        super().show()
        self.is_expanded = True
        if not self.is_pinned:
            self.check_timer.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.check_timer.stop()
            self.collapse_delay_timer.stop()
            self.expand_island()

            self.drag_position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_top_left = event.globalPosition().toPoint() - self.drag_position
            target_x: int = new_top_left.x()

            min_x: int = self.screen_geometry.left()
            max_x: int = self.screen_geometry.right() - self.island_width
            self.current_x = max(min_x, min(target_x, max_x))

            self.move(self.current_x, 0)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.current_x = self.x()
            if not self.is_pinned:
                self.check_timer.start()
            event.accept()


class ExampleFloatingIsland(FloatingIsland):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # UI 组件声明
        self.pin_btn: QPushButton
        self.label: QLabel
        self.action_btn: QPushButton

        super().__init__(parent)

    def init_widgets(self) -> None:
        # 按钮和标签布局
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
        # 设置上下左右完全居中
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.internal_widgets["label"] = self.label

        # 示例操作按钮
        self.action_btn = QPushButton("Action", self.container)
        self.action_btn.clicked.connect(lambda: print("Action clicked!"))
        layout.addWidget(self.action_btn)
        self.internal_widgets["action_btn"] = self.action_btn

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
        self.is_pinned = checked
        if self.is_pinned:
            # self.pin_btn.setText("Pinned")
            self.collapse_delay_timer.stop()
            self.expand_island()
        else:
            # self.pin_btn.setText("Pin")
            pass


def example_main() -> None:
    app = QApplication(sys.argv)

    island = ExampleFloatingIsland()
    island.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    example_main()
