# -*- coding: utf-8 -*-
"""
支持屏幕四边停靠与自动伸缩的浮岛控件
"""

import enum
import sys
from typing import Optional, cast

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QRect,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
    QSignalBlocker,
)
from PySide6.QtGui import (
    QCloseEvent,
    QContextMenuEvent,
    QCursor,
    QMouseEvent,
    QAction,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QPushButton,
    QWidget,
)

# 静态样式表: 直角矩形, 无属性选择器, 不做字符串拼接
# IslandPanel 限定只作用于顶层窗口, 不会污染子控件
ISLAND_STYLE = """
QWidget#IslandPanel {
    background-color: #1e88e5;
}
/* 静止态完全融入背景: 无底色、无边框, 只剩文字 */
QPushButton, QToolButton {
    background: transparent;
    border: none;
    color: white;
    padding: 3px 6px;
}
QPushButton:hover, QToolButton:hover {
    background-color: rgba(255, 255, 255, 35);
}
QPushButton:pressed, QToolButton:pressed {
    background-color: rgba(255, 255, 255, 55);
}
QPushButton:checked, QToolButton:checked, QToolButton:open {
    background-color: #0d47a1;
}
QPushButton::menu-indicator, QToolButton::menu-indicator {
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 8px;
}
"""


class IslandEdge(enum.Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"

    @property
    def horizontal(self) -> bool:
        # True: 沿 x 轴滑动(上/下边);
        # False: 沿 y 轴滑动(左/右边)
        return self in (IslandEdge.TOP, IslandEdge.BOTTOM)


class FloatingIsland(QWidget):
    """独立顶层浮岛"""

    # 关闭浮岛请求
    close_requested = Signal()

    # ---------- 可覆盖配置(类属性) ----------
    # 滑动轴长度 / 垂直厚度: 上/下边为 长x厚, 左/右边仍按 长x厚 摆放, 只换贴边方向
    ISLAND_LENGTH: int = 240
    PANEL_THICKNESS: int = 40
    # 0: 收缩后撤下窗口(仍响应贴边); 非 0: 保留一条该厚度的贴边细条
    COLLAPSED_STRIP: int = 5
    # 鼠标距停靠边多少像素内自动展开
    TRIGGER_MARGIN: int = 5
    # 撤下窗口时 True: 整条边任意位置可唤出; False: 仅浮岛长度范围内
    TRIGGER_WHOLE_EDGE: bool = True
    # 轮询周期(ms)
    POLL_INTERVAL: int = 100
    # 连续多少个轮询周期未悬停后收起(20 * 100ms = 2s)
    COLLAPSE_TICKS: int = 20
    # 伸缩动画时长(ms)
    ANIM_DURATION: int = 200
    # 超过该位移才认定为拖拽, 保证子控件点击不被吞掉
    DRAG_THRESHOLD: int = 4
    # 换边: 目标边间隙不得超过该值, 且要比当前边近 EDGE_STICK 以上(滞回)
    CROSSOVER_ZONE: int = 24
    EDGE_STICK: int = 10
    # False 表示永远锁在当前边
    ALLOW_EDGE_SWITCH: bool = True
    DEFAULT_STYLE: str = ISLAND_STYLE

    EDGE_ACTION_IDS: dict[IslandEdge, str] = {
        IslandEdge.TOP: "action_dock_top",
        IslandEdge.BOTTOM: "action_dock_bottom",
        IslandEdge.LEFT: "action_dock_left",
        IslandEdge.RIGHT: "action_dock_right",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        edge: IslandEdge = IslandEdge.TOP,
    ) -> None:
        self._initialized = False
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setObjectName("IslandPanel")
        # 顶层窗口必须开这个属性, 否则样式表背景不会被绘制
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # ---- 运行状态 ----
        self.edge: IslandEdge = edge
        self.is_pinned = False
        self.is_expanded = False
        self.is_dragging = False
        # 宿主席位: 任何自动逻辑都不得让浮岛出现
        self.is_hidden = False
        # 宿主已授权关闭: 放行 QCloseEvent 且不再上报
        self.is_closing = False
        self.drag_offset = QPoint()
        self.press_global = QPoint()
        self.pressed_child: Optional[QWidget] = None
        # 按下瞬间的厚度, 作换边吸附带(不随 self.edge 变化)
        self.press_thickness = 0
        self.idle_ticks = 0

        # ---- 几何 ----
        self.screen_geometry = QRect()
        # 滑动轴上的起点: 上/下边为 x, 左/右边为 y
        self.slide_pos = 0
        self.expanded_rect = QRect()
        self.collapsed_rect = QRect()

        # ---- 面板布局 ----
        self.panel_layout = QHBoxLayout(self)
        self.panel_layout.setContentsMargins(12, 4, 12, 4)
        # 允许窗口收缩到比内容最小尺寸更小
        # 否则永远收不到细条
        self.panel_layout.setSizeConstraint(
            QLayout.SizeConstraint.SetNoConstraint
        )
        self.setMinimumSize(0, 0)

        # 登记控件
        self.user_widgets: dict[str, QWidget] = {}
        self._drag_targets: set[QWidget] = set()
        self.init_user_widgets()
        # len(self.user_widgets.values()) 和 len(self._drag_targets) 应该相等。
        # 如果不等说明添加 init_user_widgets 的实现存在问题。
        assert len(self.user_widgets.values()) == len(self._drag_targets)
        self.context_menu: QMenu
        self.context_menu_dicts: dict[str, QMenu] = {}
        self.context_menu_actions: dict[str, QAction] = {}
        self.init_context_menu()
        self.setStyleSheet(self.DEFAULT_STYLE)

        # ---- 伸缩动画 ----
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(self.ANIM_DURATION)
        self.animation.finished.connect(self.on_animation_finished)

        # ---- 唯一轮询定时器: 唤出 / 延时收起 / 丢失 release 兜底 ----
        self.check_timer = QTimer(self)
        self.check_timer.setInterval(self.POLL_INTERVAL)
        self.check_timer.timeout.connect(self.check_mouse_position)

        # ---- 初始定位: 贴边且沿边居中 ----
        self.refresh_screen_geometry()
        self.recenter()
        self.update_rects()
        self.setGeometry(self.expanded_rect)
        self._initialized = True

    # ------------------------------------------------------------------
    # 子类初始化函数
    # ------------------------------------------------------------------
    def init_user_widgets(self) -> None:
        pass

    def init_context_menu(self) -> None:
        self.context_menu = QMenu(self)
        dock_menu = self.context_menu.addMenu("Dock to")
        self.context_menu_dicts["dock_menu"] = dock_menu

        for edge_enum, action_id in self.EDGE_ACTION_IDS.items():
            action_text = edge_enum.value.capitalize()
            action: QAction = dock_menu.addAction(action_text)
            action.setCheckable(True)
            action.setChecked(edge_enum is self.edge)
            action.triggered.connect(
                lambda checked=False, target=edge_enum: self.dock_to(target)
            )
            self.context_menu_actions[action_id] = action

        self.context_menu.addSeparator()
        pin_action: QAction = self.context_menu.addAction("Pin")
        pin_action.setCheckable(True)
        pin_action.setChecked(self.is_pinned)
        pin_action.toggled.connect(self.toggle_pin)
        self.context_menu_actions["pin_action"] = pin_action

        self.context_menu.addSeparator()
        quit_action: QAction = self.context_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)
        self.context_menu_actions["quit_action"] = quit_action

        # 每次弹出前同步勾选态
        self.context_menu.aboutToShow.connect(self.sync_context_menu_state)

    def sync_context_menu_state(self) -> None:
        """把菜单勾选态对齐到当前状态"""
        pin_action = self.context_menu_actions["pin_action"]
        with QSignalBlocker(pin_action):
            pin_action.setChecked(self.is_pinned)

        for edge_enum, action_id in self.EDGE_ACTION_IDS.items():
            action = self.context_menu_actions[action_id]
            action.setChecked(edge_enum is self.edge)

    # ------------------------------------------------------------------
    # 注册用户控件
    # ------------------------------------------------------------------
    def register_user_widget(self, name: str, widget: QWidget) -> None:
        """注册控件挂上事件过滤器以支持拖拽"""
        self.user_widgets[name] = widget
        widget.installEventFilter(self)
        self._drag_targets.add(widget)

    def unregister_user_widget(self, name: str) -> None:
        """移除注册控件"""
        widget = self.user_widgets.pop(name, None)
        if widget is not None:
            widget.removeEventFilter(self)
            self._drag_targets.discard(widget)

    # ------------------------------------------------------------------
    # 几何计算
    # ------------------------------------------------------------------
    def along_length(self) -> int:
        # 滑动轴长度: 上/下边取长, 左/右边取厚
        return (
            self.ISLAND_LENGTH if self.edge.horizontal else self.PANEL_THICKNESS
        )

    def thickness(self) -> int:
        # 垂直于停靠边的厚度: 上/下边取厚, 左/右边取长
        return (
            self.PANEL_THICKNESS if self.edge.horizontal else self.ISLAND_LENGTH
        )

    def refresh_screen_geometry(self) -> None:
        """刷新所在屏幕几何(多显示器跟随当前屏)。"""
        screen = QApplication.screenAt(self.geometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()

        # availableGeometry 避开任务栏
        geo = screen.availableGeometry()
        if geo != self.screen_geometry:
            self.screen_geometry = geo
            self.update_rects()

    def recenter(self) -> None:
        """沿停靠边居中。"""
        geo = self.screen_geometry
        along = self.along_length()
        if self.edge.horizontal:
            self.slide_pos = geo.x() + (geo.width() - along) // 2
        else:
            self.slide_pos = geo.y() + (geo.height() - along) // 2

    def edge_coord(self) -> int:
        """停靠边在法向上的坐标(下/右边取屏幕内侧的边界线)。"""
        geo = self.screen_geometry
        if self.edge is IslandEdge.TOP:
            return geo.top()
        if self.edge is IslandEdge.BOTTOM:
            return geo.bottom()
        if self.edge is IslandEdge.LEFT:
            return geo.left()
        return geo.right()

    def perpendicular_start(self, extent: int) -> int:
        """法向上贴合停靠边的起始坐标。"""
        # 下/右边的外沿在边界线 +1 处, 需反向退掉一个 extent
        if self.edge in (IslandEdge.BOTTOM, IslandEdge.RIGHT):
            return self.edge_coord() + 1 - extent
        return self.edge_coord()

    def update_rects(self) -> None:
        """按当前停靠边重算展开/收缩矩形(绝对坐标), 并钳位滑动轴。"""
        geo = self.screen_geometry
        along = self.along_length()
        perp = self.thickness()
        # 收缩态至少 1px, 避免零尺寸窗口
        strip = max(1, self.COLLAPSED_STRIP)

        if self.edge.horizontal:
            low, high = geo.left(), geo.right() + 1 - along
        else:
            low, high = geo.top(), geo.bottom() + 1 - along
        self.slide_pos = max(low, min(self.slide_pos, max(low, high)))

        if self.edge.horizontal:
            self.expanded_rect = QRect(
                self.slide_pos, self.perpendicular_start(perp), along, perp
            )
            self.collapsed_rect = QRect(
                self.slide_pos, self.perpendicular_start(strip), along, strip
            )
        else:
            self.expanded_rect = QRect(
                self.perpendicular_start(perp), self.slide_pos, perp, along
            )
            self.collapsed_rect = QRect(
                self.perpendicular_start(strip), self.slide_pos, strip, along
            )

    def is_in_slide_range(self, point: QPoint) -> bool:
        """鼠标是否落在滑动轴方向的长度区间内。"""
        axis = point.x() if self.edge.horizontal else point.y()
        return self.slide_pos <= axis < self.slide_pos + self.along_length()

    def distance_to_edge(self, point: QPoint) -> int:
        """鼠标到当前停靠边的带方向距离(移出屏幕外为负)。"""
        axis = point.y() if self.edge.horizontal else point.x()
        delta = axis - self.edge_coord()
        # 上/左边向外为正, 下/右边向外为负
        return (
            delta if self.edge in (IslandEdge.TOP, IslandEdge.LEFT) else -delta
        )

    def is_in_trigger_zone(self, point: QPoint) -> bool:
        """是否处于贴边触发区。"""
        near_edge = self.distance_to_edge(point) < self.TRIGGER_MARGIN

        # 已撤下窗口时, 整条边都能唤出, 不要求落在长度区间内
        if self.COLLAPSED_STRIP == 0 and self.TRIGGER_WHOLE_EDGE:
            return near_edge

        return near_edge and self.is_in_slide_range(point)

    def gaps_to_edges(self, rect: QRect) -> dict[IslandEdge, int]:
        """矩形到四条边的间隙。"""
        geo = self.screen_geometry
        return {
            IslandEdge.TOP: rect.top() - geo.top(),
            IslandEdge.BOTTOM: geo.bottom() - rect.bottom(),
            IslandEdge.LEFT: rect.left() - geo.left(),
            IslandEdge.RIGHT: geo.right() - rect.right(),
        }

    def detect_edge(self, rect: QRect) -> IslandEdge:
        """换边判定: 先脱离按下时那条边的吸附带, 再贴到目标边。"""
        if not self.ALLOW_EDGE_SWITCH:
            return self.edge

        gaps = self.gaps_to_edges(rect)
        # 用按下时的厚度快照, 否则换到左/右边后带变成 240, 永远换不回来
        if gaps[self.edge] <= self.press_thickness:
            return self.edge

        nearest = min(gaps, key=gaps.__getitem__)
        if nearest is self.edge or gaps[nearest] > self.CROSSOVER_ZONE:
            return self.edge

        # 滞回: 目标边要明显更近才切换, 防止边界处抖动
        return (
            nearest
            if gaps[nearest] + self.EDGE_STICK < gaps[self.edge]
            else self.edge
        )

    # ------------------------------------------------------------------
    # 展开 / 收缩(仅供内部自动逻辑调用)
    # ------------------------------------------------------------------
    def expand_island(self, animate: bool = True) -> None:
        # 隐藏与关闭状态优先
        if self.is_closing or self.is_hidden:
            return

        self.update_rects()
        target = self.expanded_rect
        self.is_expanded = True

        # 走 QWidget 层唤回撤下的窗口, 不碰宿主语义的 show()
        if not self.isVisible():
            super().show()
        self.set_user_widgets_visible(True)

        if self.geometry() == target:
            return

        self.animation.stop()
        if animate:
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target)
            self.animation.start()
        else:
            self.setGeometry(target)

    def collapse_island(self) -> None:
        # 固定/拖拽中/已隐藏/已关闭/有弹窗/鼠标仍在窗口上, 都不收起
        if (
            not self.is_expanded
            or self.is_pinned
            or self.is_dragging
            or self.is_hidden
            or self.is_closing
            or QApplication.activePopupWidget() is not None
            or self.geometry().contains(QCursor.pos())
        ):
            return

        self.is_expanded = False
        self.idle_ticks = 0
        self.update_rects()
        # 先藏控件, 细条里只剩纯色底, 不会被按钮撑出裁切痕迹
        self.set_user_widgets_visible(False)

        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.collapsed_rect)
        self.animation.start()

    def on_animation_finished(self) -> None:
        # 收缩到位且不留细条时整体撤下窗口
        # 用 setVisible(False) 而非 hide(): 后者会停掉 check_timer, 贴边就唤不回来了
        if self.COLLAPSED_STRIP == 0 and not (
            self.is_expanded or self.is_dragging or self.is_hidden
        ):
            self.setVisible(False)

    def set_user_widgets_visible(self, visible: bool) -> None:
        for widget in self.user_widgets.values():
            widget.setVisible(visible)

    # ------------------------------------------------------------------
    # 鼠标监测(唯一轮询入口)
    # ------------------------------------------------------------------
    def check_mouse_position(self) -> None:
        # 拖拽中只做兜底: 左键已松开却仍在拖拽, 说明 release 事件丢了
        if self.is_dragging:
            if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                self._end_drag()
            return

        if self.is_pinned or QApplication.activePopupWidget() is not None:
            return

        point = QCursor.pos()
        hovering = self.isVisible() and self.geometry().contains(point)
        if self.is_in_trigger_zone(point) or hovering:
            self.idle_ticks = 0
            self.expand_island()
            return

        if not (self.isVisible() and self.is_expanded):
            return

        self.idle_ticks += 1
        if self.idle_ticks >= self.COLLAPSE_TICKS:
            self.collapse_island()

    # ------------------------------------------------------------------
    # 拖拽支持
    # ------------------------------------------------------------------
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """把子控件上的鼠标事件转成浮岛拖拽, 同时保留正常点击。"""
        # QMouseEvent 覆盖 press/move/release/dblclick, wheel/hover 不会误入
        if obj not in self._drag_targets or not isinstance(event, QMouseEvent):
            return super().eventFilter(obj, event)

        event_type = event.type()
        is_left = event.button() == Qt.MouseButton.LeftButton

        if event_type == QEvent.Type.MouseButtonPress and is_left:
            self.pressed_child = cast(QWidget, obj)
            self._handle_press(event.globalPosition().toPoint())
            # 放行, 让按钮维持自身的按下/悬停状态
            return False

        if event_type == QEvent.Type.MouseMove:
            self._handle_move(event.globalPosition().toPoint(), event.buttons())
            return False

        if event_type == QEvent.Type.MouseButtonRelease and is_left:
            # 拖拽过就吞掉本次释放, 纯点击原样放行给按钮
            return self._end_drag()

        if event_type == QEvent.Type.MouseButtonDblClick and is_left:
            return self.is_dragging

        return super().eventFilter(obj, event)

    def _handle_press(self, global_pos: QPoint) -> None:
        """按下: 先展开面板再算抓取点, 四边坐标系才一致。"""
        self.press_global = global_pos
        self.press_thickness = self.thickness()
        self.idle_ticks = 0

        self.expand_island(animate=False)
        self.drag_offset = global_pos - self.pos()
        if not self.is_closing:
            self.check_timer.start()

    def _handle_move(self, global_pos: QPoint, buttons: Qt.MouseButton) -> None:
        """移动: 未过阈值视为点击, 过阈值才升级为拖拽。"""
        if not (buttons & Qt.MouseButton.LeftButton):
            if self.is_dragging:
                self._end_drag()
            return

        if not self.is_dragging:
            delta = global_pos - self.press_global
            if max(abs(delta.x()), abs(delta.y())) < self.DRAG_THRESHOLD:
                return
            self._begin_drag()

        self.refresh_screen_geometry()
        top_left = global_pos - self.drag_offset
        # 拖拽期间宽高恒定, 用配置尺寸构造虚拟矩形即可
        free = QRect(
            top_left.x(), top_left.y(), self.ISLAND_LENGTH, self.PANEL_THICKNESS
        )

        candidate = self.detect_edge(free)
        if candidate is not self.edge:
            self.edge = candidate
            # 换边重置抓取点: 主轴保持连续, 法向交给贴边逻辑
            half_perp = self.thickness() // 2
            if candidate.horizontal:
                self.drag_offset = QPoint(self.drag_offset.x(), half_perp)
            else:
                self.drag_offset = QPoint(half_perp, self.drag_offset.y())

        # 只改滑动轴坐标, 宽高恒定 -> 控件位置与比例不受影响
        self.slide_pos = free.x() if self.edge.horizontal else free.y()
        self.update_rects()

        self.animation.stop()
        self.setGeometry(self.expanded_rect)

    def _begin_drag(self) -> None:
        self.is_dragging = True

        child = self.pressed_child
        if isinstance(child, QAbstractButton):
            # 释放事件会被吞掉, 手动清按下态, 否则按钮卡在按下外观
            child.setDown(False)

        # 从菜单按钮起拖时, 顺手关掉已弹出的菜单
        popup = QApplication.activePopupWidget()
        if popup is not None:
            popup.hide()

    def _end_drag(self) -> bool:
        """结束拖拽: 幂等, 可从过滤器/窗口事件/轮询兜底任意路径调用。"""
        was_dragging = self.is_dragging
        self.is_dragging = False
        self.pressed_child = None

        if was_dragging:
            self.refresh_screen_geometry()
            self.update_rects()
            self.setGeometry(self.expanded_rect)

        # 不补 singleShot: 常驻 check_timer 最多一个周期后自然发现鼠标已离开
        if not (self.is_pinned or self.is_hidden or self.is_closing):
            self.idle_ticks = 0
            self.check_timer.start()

        return was_dragging

    # ------------------------------------------------------------------
    # 运行时收尾
    # ------------------------------------------------------------------
    def _teardown_runtime(self) -> None:
        """停掉所有运行时活动(动画/轮询/拖拽态), 幂等。"""
        self.animation.stop()
        self.check_timer.stop()
        self.is_dragging = False
        self.pressed_child = None
        self.idle_ticks = 0

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------
    def dock_to(self, edge: IslandEdge, animate: bool = True) -> None:
        """主动停靠到指定边(右键菜单调用, 比拖拽换边更确定)。"""
        if self.is_closing:
            return

        axis_changed = self.edge.horizontal != edge.horizontal
        self.edge = edge
        # 先刷新屏幕几何, 否则 recenter() 会按过期范围居中
        self.refresh_screen_geometry()
        if axis_changed:
            self.recenter()

        self.update_rects()
        self.animation.stop()
        # 宿主收着时只更新几何与停靠边, 不擅自把窗口亮出来
        self.expand_island(animate=animate)

    def toggle_pin(self, checked: bool) -> None:
        self.is_pinned = checked
        if self.is_pinned:
            self.idle_ticks = 0
            self.expand_island()
            return

        # 取消固定必须把轮询接回来, 否则自动收起与拖拽兜底都失效
        if not self.is_hidden and not self.is_closing:
            self.idle_ticks = 0
            self.check_timer.start()

    def shutdown(self) -> None:
        """
        已决定退出时调用。
        调用后窗口停止全部自动交互，保持静默状态。
        如果需要关闭窗口请手动调用 close()
        """
        if self.is_closing:
            return
        self._teardown_runtime()
        self.is_closing = True

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_closing:
            super().closeEvent(event)
            return

        event.ignore()
        self.close_requested.emit()

    def hide(self) -> None:
        self.is_hidden = True
        self.is_expanded = False
        # 动画不停的话 finished 回调会在隐藏期间继续搬动窗口
        self._teardown_runtime()
        super().hide()

    def show(self) -> None:
        if self.is_closing:
            return

        self.is_hidden = False
        self.refresh_screen_geometry()
        # 只钳位不重新居中, 否则 hide/show 往返会抹掉用户拖好的位置
        self.update_rects()
        super().show()
        self.is_expanded = True
        self.setGeometry(self.expanded_rect)
        self.set_user_widgets_visible(True)
        self.press_thickness = self.thickness()
        self.idle_ticks = 0
        if not self.is_pinned:
            self.check_timer.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.pressed_child = None
        self._handle_press(event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._handle_move(event.globalPosition().toPoint(), event.buttons())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        # 与过滤器共用收尾, _end_drag 幂等
        self._end_drag()
        event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.context_menu.exec(event.globalPos())

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange and self._initialized:
            QTimer.singleShot(0, self, self.retranslate)
        super().changeEvent(event)

    def retranslate(self) -> None:
        self.context_menu_dicts["dock_menu"].setTitle(self.tr("Dock to"))
        edge_actions_text: dict[str, str] = {
            self.EDGE_ACTION_IDS[IslandEdge.TOP]: self.tr("Top"),
            self.EDGE_ACTION_IDS[IslandEdge.BOTTOM]: self.tr("Bottom"),
            self.EDGE_ACTION_IDS[IslandEdge.LEFT]: self.tr("Left"),
            self.EDGE_ACTION_IDS[IslandEdge.RIGHT]: self.tr("Right"),
        }
        for action_id, text in edge_actions_text.items():
            self.context_menu_actions[action_id].setText(text)
        self.context_menu_actions["pin_action"].setText(self.tr("Pin"))
        self.context_menu_actions["quit_action"].setText(self.tr("Quit"))


class ExampleFloatingIsland(FloatingIsland):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        edge: IslandEdge = IslandEdge.TOP,
    ) -> None:
        # 类型声明: 实例在 init_user_widgets() 中创建
        self.pin_btn: QPushButton
        super().__init__(parent, edge)

    def init_user_widgets(self) -> None:
        # 布局方向与停靠边无关, 换边不重排
        self.pin_btn = QPushButton("Pin", self)
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self.toggle_pin)
        self.panel_layout.addWidget(self.pin_btn)
        self.register_user_widget("pin_btn", self.pin_btn)

        label = QLabel("Island", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent;"
        )
        self.panel_layout.addWidget(label)
        self.register_user_widget("label", label)

        action_btn = QPushButton("Menu", self)
        menu = QMenu(action_btn)
        menu.addAction("Example option 1")
        menu.addAction("Example option 2")
        action_btn.setMenu(menu)
        self.panel_layout.addWidget(action_btn)
        self.register_user_widget("action_menu", action_btn)

    def toggle_pin(self, checked: bool) -> None:
        # 菜单与按钮共用同一状态: 任一入口都要把按钮外观同步过来
        super().toggle_pin(checked)
        self.pin_btn.setChecked(checked)


def example_main() -> None:
    app = QApplication(sys.argv)

    # 不传 parent: 浮岛必须是独立顶层窗口
    # COLLAPSED_STRIP 沿用默认值 5: 收起后留一条贴边细条
    # 若要彻底撤下窗口, 在实例上设 island.COLLAPSED_STRIP = 0
    island = ExampleFloatingIsland(edge=IslandEdge.TOP)
    # island.COLLAPSED_STRIP = 0
    # 独立运行没有宿主, 把关闭请求直接接到事件循环退出上
    island.close_requested.connect(app.quit)
    island.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    example_main()
