import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QInputDialog

from data.keyboard_shift_symbol import SHIFT_SYMBOL
from ui.ui_resource import custom_key_ui


class CustomKeyDialog(QDialog, custom_key_ui.Ui_CustomKeyDialog):
    custom_key_send_signal = Signal(list)
    custom_key_save_signal = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(
            Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        self.shortcut_key_clear()
        self.key_sequence_edit.keySequenceChanged.connect(
            self.shortcut_key_changed
        )
        self.push_button_save.clicked.connect(self.shortcut_key_save)
        self.push_button_send.clicked.connect(self.shortcut_key_send)
        self.push_button_clear.clicked.connect(self.shortcut_key_clear)

    def shortcut_key_changed(self) -> None:
        key_sequence = self.key_sequence_edit.keySequence()
        if key_sequence.count() == 0:
            # key_sequence = ""
            return
        if key_sequence.count() == 1:
            key_sequence = key_sequence.toString()
        else:
            key_sequence_list = key_sequence.toString().split(",")
            # self.key_sequence_edit.setKeySequence(key_sequence_list[0])
            key_sequence = key_sequence_list[0]

        key_sequence_list = key_sequence.split("+")
        for key_symbol in key_sequence_list:
            if key_symbol in SHIFT_SYMBOL:
                key_sequence = "Shift+" + key_sequence
                break

        # 没有匹配到+号，不是组合键
        if len(re.findall("\\+", key_sequence)) == 0:
            self.key_sequence_edit.setKeySequence(key_sequence)
        elif key_sequence == "+":
            self.key_sequence_edit.setKeySequence(key_sequence)
        else:
            # key_sequence != "+"
            key_sequence_list = key_sequence.split(
                "+"
            ).copy()  # 将复合键转换为功能键
            if "Ctrl" in key_sequence_list:
                self.push_button_ctrl.setChecked(True)
            else:
                self.push_button_ctrl.setChecked(False)

            if "Alt" in key_sequence_list:
                self.push_button_alt.setChecked(True)
            else:
                self.push_button_alt.setChecked(False)

            if "Shift" in key_sequence_list:
                self.push_button_shift.setChecked(True)
            else:
                self.push_button_shift.setChecked(False)

            if "Meta" in key_sequence_list:
                self.push_button_meta.setChecked(True)
            else:
                self.push_button_meta.setChecked(False)

            key_sequence = key_sequence_list[-1]
        self.key_sequence_edit.setKeySequence(key_sequence)
        pass

    def shortcut_key_clear(self) -> None:
        self.push_button_ctrl.setChecked(False)
        self.push_button_alt.setChecked(False)
        self.push_button_shift.setChecked(False)
        self.push_button_meta.setChecked(False)
        self.push_button_tab.setChecked(False)
        self.push_button_prtsc.setChecked(False)
        self.key_sequence_edit.setKeySequence("")

    def shortcut_key_buffer(self) -> list[str]:
        buffer = list()
        if self.push_button_ctrl.isChecked() is True:
            buffer.append("ctrl_left")
        if self.push_button_alt.isChecked() is True:
            buffer.append("alt_left")
        if self.push_button_shift.isChecked() is True:
            buffer.append("shift_left")
        if self.push_button_meta.isChecked() is True:
            buffer.append("win_left")
        if self.push_button_tab.isChecked() is True:
            buffer.append("tab")
        if self.push_button_prtsc.isChecked() is True:
            buffer.append("print_screen")
        key_sequence = self.key_sequence_edit.keySequence().toString()
        if key_sequence == "":
            # buffer.clear()
            pass
        else:
            buffer.append(key_sequence.lower())
        return buffer

    def shortcut_key_save(self):
        buffer = self.shortcut_key_buffer()
        text, status = QInputDialog.getText(
            self, self.tr("Save shortcut key"), self.tr("Shortcut name:")
        )
        if status:
            self.custom_key_save_signal.emit(text, buffer)
            self.close()

    def shortcut_key_send(self):
        buffer = self.shortcut_key_buffer()
        self.custom_key_send_signal.emit(buffer)


if __name__ == "__main__":
    pass
