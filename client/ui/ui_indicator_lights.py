from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog

from keyboard_buffer import KeyboardIndicatorBuffer
from ui.ui_resource import indicator_lights_ui


class IndicatorLightsDialog(
    QDialog, indicator_lights_ui.Ui_IndicatorLightsDialog
):
    lock_key_clicked_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.keyboard_indicator_lights = KeyboardIndicatorBuffer()
        self.push_button_num_lock.clicked.connect(
            lambda clicked: self.lock_key_clicked_signal.emit("num_lock")
        )
        self.push_button_caps_lock.clicked.connect(
            lambda clicked: self.lock_key_clicked_signal.emit("caps_lock")
        )
        self.push_button_scroll_lock.clicked.connect(
            lambda clicked: self.lock_key_clicked_signal.emit("scroll_lock")
        )

    def update_buffer(self, buffer: KeyboardIndicatorBuffer):
        self.keyboard_indicator_lights = buffer
        pass

    def refresh_status_from_buffer(self):
        self.push_button_num_lock.setChecked(
            self.keyboard_indicator_lights.num_lock
        )
        self.push_button_caps_lock.setChecked(
            self.keyboard_indicator_lights.caps_lock
        )
        self.push_button_scroll_lock.setChecked(
            self.keyboard_indicator_lights.scroll_lock
        )

    def refresh_status_from_ui(self):
        if (
            self.push_button_num_lock.isChecked()
            == self.keyboard_indicator_lights.num_lock
        ):
            self.keyboard_indicator_lights.num_lock = (
                self.push_button_num_lock.isChecked()
            )
            self.lock_key_clicked_signal.emit("num_lock")
        if (
            self.push_button_caps_lock.isChecked()
            == self.keyboard_indicator_lights.caps_lock
        ):
            self.keyboard_indicator_lights.caps_lock = (
                self.push_button_caps_lock.isChecked()
            )
            self.lock_key_clicked_signal.emit("caps_lock")
        if (
            self.push_button_scroll_lock.isChecked()
            == self.keyboard_indicator_lights.scroll_lock
        ):
            self.keyboard_indicator_lights.scroll_lock = (
                self.push_button_scroll_lock.isChecked()
            )
            self.lock_key_clicked_signal.emit("scroll_lock")


if __name__ == "__main__":
    pass
