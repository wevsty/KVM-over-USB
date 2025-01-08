import PySide6
from PySide6.QtWidgets import QCheckBox, QMessageBox


class MessageBox(QMessageBox):
    def __init__(self, parent: PySide6.QtWidgets.QWidget | None= ...) -> None:
        super().__init__(parent)

    @staticmethod
    def optional_information(
            parent: PySide6.QtWidgets.QWidget,
            title: str,
            text: str,
            optional_text: str = "Don't show this again",
            optional_checked: bool = False,
            buttons: PySide6.QtWidgets.QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
            default_button: PySide6.QtWidgets.QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton
            ) -> (PySide6.QtWidgets.QMessageBox.StandardButton, bool):
        msg = MessageBox(parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(title)
        # msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        msg.setDefaultButton(default_button)
        checkbox = QCheckBox(optional_text)
        checkbox.setChecked(optional_checked)
        msg.setCheckBox(checkbox)
        button_value = msg.exec()
        checkbox_status = checkbox.isChecked()
        return button_value, checkbox_status

if __name__ == "__main__":
    # MessageBox.optional_information(None,"1","2","3")
    pass
