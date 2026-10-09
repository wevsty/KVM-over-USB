from __future__ import annotations
import keyboard_buffer

import collections
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QStatusBar
from .keyboard_code_data import KeyboardCodeData


class MainWindowStatusBarManager:
    def __init__(self, status_bar: QStatusBar):
        self.status_bar_labels: collections.OrderedDict[str, QLabel] = (
            collections.OrderedDict()
        )
        self.keyboard_hid_code_data = KeyboardCodeData()
        self.current_message: str = ""
        self.status_bar: QStatusBar = status_bar
        self.init_status_bar()

    def init_status_bar(self) -> None:
        self.init_labels()
        # 设置样式
        self.status_bar.setStyleSheet("padding: 0px;")
        # 设置分割线
        self.status_bar.addPermanentWidget(QLabel())
        # 把 labels 加入状态栏
        for _, label_object in self.status_bar_labels.items():
            self.status_bar.addPermanentWidget(label_object)
        # 增加一个空 label 占位
        self.status_bar.addPermanentWidget(QLabel())
        self.status_bar.reformat()

    def init_labels(self) -> None:
        self.status_bar_labels["CTRL"] = QLabel()
        self.status_bar_labels["SHIFT"] = QLabel()
        self.status_bar_labels["ALT"] = QLabel()
        self.status_bar_labels["META"] = QLabel()
        self.status_bar_labels["CAPS_LOCK"] = QLabel()
        self.status_bar_labels["NUM_LOCK"] = QLabel()
        self.status_bar_labels["SCR_LOCK"] = QLabel()

        # 设置显示文字
        self.status_bar_labels["CTRL"].setText("CTRL")
        self.status_bar_labels["SHIFT"].setText("SHIFT")
        self.status_bar_labels["ALT"].setText("ALT")
        self.status_bar_labels["META"].setText("META")
        self.status_bar_labels["CAPS_LOCK"].setText("CAPS")
        self.status_bar_labels["NUM_LOCK"].setText("NUM")
        self.status_bar_labels["SCR_LOCK"].setText("SCR")

        # 设置字体
        font = QFont()
        font.setBold(True)
        # font.setPointSize(10)

        for _, label_object in self.status_bar_labels.items():
            # 设置字体
            label_object.setFont(font)
            # 设置样式
            label_object.setStyleSheet("color: grey")
            # 设置聚焦方式
            label_object.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def get(self) -> QStatusBar:
        return self.status_bar

    # 设置 label 指示状态
    def update_label_indication_status(self, label_name: str, enable: bool):
        if enable:
            self.status_bar_labels[label_name].setStyleSheet("color: black")
        else:
            self.status_bar_labels[label_name].setStyleSheet("color: grey")

    # 通过键盘缓冲区更新 label 显示
    def update_label_status(
        self,
        key_buffer: keyboard_buffer.KeyboardKeyBuffer,
        indication_buffer: keyboard_buffer.KeyboardIndicatorBuffer,
    ):
        _, ctrl_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "ctrl_left"
        )
        _, ctrl_right = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "ctrl_right"
            )
        )
        if key_buffer.is_pressed(ctrl_left) or key_buffer.is_pressed(
            ctrl_right
        ):
            self.update_label_indication_status("CTRL", True)
        else:
            self.update_label_indication_status("CTRL", False)

        _, shift_left = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "shift_left"
            )
        )
        _, shift_right = (
            self.keyboard_hid_code_data.convert_key_name_to_hid_code(
                "shift_right"
            )
        )
        if key_buffer.is_pressed(shift_left) or key_buffer.is_pressed(
            shift_right
        ):
            self.update_label_indication_status("SHIFT", True)
        else:
            self.update_label_indication_status("SHIFT", False)

        _, alt_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "alt_left"
        )
        _, alt_right = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "alt_right"
        )
        if key_buffer.is_pressed(alt_left) or key_buffer.is_pressed(alt_right):
            self.update_label_indication_status("ALT", True)
        else:
            self.update_label_indication_status("ALT", False)

        _, win_left = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "win_left"
        )
        _, win_right = self.keyboard_hid_code_data.convert_key_name_to_hid_code(
            "win_right"
        )
        if key_buffer.is_pressed(win_left) or key_buffer.is_pressed(win_right):
            self.update_label_indication_status("META", True)
        else:
            self.update_label_indication_status("META", False)

        self.update_label_indication_status(
            "CAPS_LOCK", indication_buffer.caps_lock
        )
        self.update_label_indication_status(
            "NUM_LOCK", indication_buffer.num_lock
        )
        self.update_label_indication_status(
            "SCR_LOCK", indication_buffer.scroll_lock
        )

    def show_message(self, text: str):
        if not self.current_message == text:
            self.status_bar.showMessage(text)
        else:
            self.current_message = text
