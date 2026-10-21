from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class FloatingBall(QWidget):
    """悬浮球组件

    作为独立的无边框工具窗口悬浮在父窗口之上, 因此不会被父窗口内
    的 RHI/GPU 渲染内容(例如 QVideoWidget)覆盖.

    鼠标左键单击(未发生拖动)时发出 clicked 信号, 按住左键拖动时
    悬浮球会被限制在父窗口范围内移动, 并跟随父窗口移动与显隐.
    """

    clicked = Signal()

    # 默认直径
    DEFAULT_DIAMETER: int = 48
    # 绘制时保留的边缘宽度
    PAINT_MARGIN: int = 2

    def __init__(self, parent: QWidget | None = None):
        # 以父窗口为 owner 的顶层工具窗口(不显示在任务栏),
        # 并且不接受键盘焦点, 避免点击悬浮球后主窗口键盘输入失效
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self._icon: QIcon = QIcon()
        self._hover: bool = False
        self._pressed: bool = False
        self._dragging: bool = False
        self._press_pos: QPoint = QPoint()
        # 按下时鼠标全局位置与悬浮球左上角的偏移(全局逻辑像素)
        self._grab_offset: QPoint = QPoint()
        # 相对父窗口客户区的位置
        self._relative_pos: QPoint = QPoint(0, 0)
        # 悬浮球是否启用(关闭后即使父窗口显隐也不应重新显示)
        self._enabled: bool = True

        self.setFixedSize(self.DEFAULT_DIAMETER, self.DEFAULT_DIAMETER)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 跟随父窗口的移动/缩放/显隐
        if parent is not None:
            parent.installEventFilter(self)

    # 直径(取宽高中较小的值)
    def diameter(self) -> int:
        return min(self.width(), self.height())

    # 设置直径
    def set_diameter(self, diameter: int) -> None:
        self.setFixedSize(diameter, diameter)

    # 设置显示的图标
    def set_icon(self, icon: QIcon) -> None:
        self._icon = icon
        self.update()

    # 设置是否保持在最前(与父窗口的置顶状态保持一致)
    def set_topmost(self, enable: bool) -> None:
        flags = self.windowFlags()
        if enable:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # 重新设置窗口标志后窗口会被隐藏, 需要重新显示
        if self._enabled:
            self.show()

    # 设置是否启用悬浮球(关闭后跟随父窗口显隐时不再重新显示)
    def set_enabled(self, enable: bool) -> None:
        self._enabled = enable
        if enable:
            self.show()
        else:
            self.hide()

    # 图标绘制区域
    def icon_rect(self) -> QRect:
        margin: int = self.diameter() // 4
        return self.rect().adjusted(margin, margin, -margin, -margin)

    # 菜单弹出位置(组件左下角)
    def menu_popup_position(self) -> QPoint:
        return self.mapToGlobal(QPoint(0, self.height()))

    # 按父窗口客户区坐标移动悬浮球, 并保证悬浮球在父窗口范围内
    def move_into_parent(self, pos: QPoint) -> None:
        parent: QWidget | None = self.parentWidget()
        if parent is None:
            self._relative_pos = QPoint(pos)
            self.move(pos)
            return
        pos.setX(max(0, min(pos.x(), parent.width() - self.width())))
        pos.setY(max(0, min(pos.y(), parent.height() - self.height())))
        self._relative_pos = QPoint(pos)
        self.move(parent.mapToGlobal(pos))

    # 按当前相对位置重新对齐到父窗口
    def follow_parent(self) -> None:
        self.move_into_parent(QPoint(self._relative_pos))

    # 当前状态对应的背景颜色
    def background_color(self) -> QColor:
        if self._pressed:
            return QColor(20, 22, 26, 235)
        if self._hover:
            return QColor(60, 64, 72, 230)
        return QColor(36, 38, 44, 200)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.background_color())
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
        painter.drawEllipse(
            self.rect().adjusted(
                self.PAINT_MARGIN,
                self.PAINT_MARGIN,
                -self.PAINT_MARGIN,
                -self.PAINT_MARGIN,
            )
        )
        if not self._icon.isNull():
            self._icon.paint(painter, self.icon_rect())

    # 父窗口移动/缩放/显隐时保持悬浮球跟随
    def eventFilter(self, watched, event) -> bool:
        if watched is self.parentWidget():
            event_type = event.type()
            if event_type in (QEvent.Type.Move, QEvent.Type.Resize):
                # 拖拽过程中以鼠标为准, 忽略父窗口的跟随, 避免来回拉扯
                if self._dragging:
                    return super().eventFilter(watched, event)
                self.follow_parent()
            elif event_type == QEvent.Type.Show:
                if self._enabled:
                    self.show()
            elif event_type == QEvent.Type.Hide:
                self.hide()
        return super().eventFilter(watched, event)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # 鼠标事件在本组件内消化, 避免触发父窗口的鼠标捕获
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_pos = event.globalPosition().toPoint()
            # 记录鼠标相对悬浮球左上角的偏移(全局逻辑坐标), 全程保持同一坐标系,
            # 以免高 DPI 下被缩放成倍放大
            self._grab_offset = self._press_pos - self.frameGeometry().topLeft()
            self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # 未按下时不处理事件, 使其继续传递给父窗口更新鼠标位置
        if not self._pressed:
            super().mouseMoveEvent(event)
            return
        delta: QPoint = event.globalPosition().toPoint() - self._press_pos
        # 超过拖拽阈值后才认为是拖动, 避免影响单击
        if not self._dragging:
            drag_distance: int = max(QApplication.startDragDistance(), 1)
            if delta.manhattanLength() < drag_distance:
                event.accept()
                return
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        # 期望的悬浮球左上角全局位置(全部位于同一全局逻辑坐标系)
        desired: QPoint = event.globalPosition().toPoint() - self._grab_offset
        parent: QWidget | None = self.parentWidget()
        if parent is not None:
            # 在全局逻辑坐标内约束到父窗口客户区, 与 move() 使用同一坐标系
            client = parent.geometry()
            x = max(
                client.left(),
                min(desired.x(), client.right() - self.width()),
            )
            y = max(
                client.top(),
                min(desired.y(), client.bottom() - self.height()),
            )
            pos = QPoint(x, y)
            self._relative_pos = pos - client.topLeft()
            self.move(pos)
        else:
            self._relative_pos = desired
            self.move(desired)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.accept()
            return
        # 没有产生拖动则认为是一次单击
        trigger_clicked: bool = not self._dragging
        self._pressed = False
        self._dragging = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        if trigger_clicked and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.accept()


if __name__ == "__main__":
    pass
