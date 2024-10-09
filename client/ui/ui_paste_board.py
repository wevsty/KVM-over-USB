import base64
import os
from typing import Optional

from PySide6.QtCore import Signal, Qt, QThread, QObject
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ui.ui_resource import paste_board_ui


class SendDataWorker(QObject):
    send_string_signal = Signal(str)
    send_progress_value_signal = Signal(int)
    send_text_signal = Signal(str)
    send_file_signal = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.flag_stop = False
        self.flag_sending = False
        self.send_text_signal.connect(self.send_text)
        self.send_file_signal.connect(self.send_file)

    def is_sending(self):
        return self.flag_sending

    def send_string_data(self, data: str) -> None:
        for character in data:
            self.send_string_signal.emit(character)
            QThread.msleep(50)
            if self.flag_stop:
                break

    def send_text(self, data: str) -> None:
        self.flag_stop = False
        self.flag_sending = True
        self.send_string_data(data)
        self.flag_sending = False

    def send_file(self, file_path: str) -> None:
        self.flag_stop = False
        self.flag_sending = True
        file_name = os.path.basename(file_path)
        buffer_size = 512
        command_template = "echo -e -n \"{}\" | base64 -d >> ./{}\n"
        sent_bytes = 0
        total_bytes = os.path.getsize(file_path)
        display_progress_value = 0
        self.send_progress_value_signal.emit(display_progress_value)
        with open(file_path, "rb") as fp:
            while True:
                binary_data = fp.read(buffer_size)
                if not binary_data:
                    break
                base64_data = base64.b64encode(binary_data).decode()
                write_buffer = command_template.format(base64_data, file_name)
                self.send_string_data(write_buffer)
                sent_bytes += len(binary_data)
                progress_value = int(sent_bytes / total_bytes * 100)
                if display_progress_value < progress_value:
                    display_progress_value = progress_value
                    self.send_progress_value_signal.emit(progress_value)
                if self.flag_stop:
                    break
        display_progress_value = 100
        self.send_progress_value_signal.emit(display_progress_value)
        self.flag_sending = False
        pass


class PasteBoardDialog(QDialog, paste_board_ui.Ui_PasteBoardDialog):
    send_string_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.push_button_file_select.clicked.connect(self.select_file_button_clicked)
        self.push_button_send.clicked.connect(self.send_button_clicked)
        self.push_button_stop.clicked.connect(self.stop_button_clicked)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.file_path = None
        self.thread = QThread()
        self.send_worker = SendDataWorker()
        self.send_worker.send_progress_value_signal.connect(self.update_progress_bar)
        self.send_worker.send_string_signal.connect(self.send_string_signal)
        self.send_worker.moveToThread(self.thread)

    def exec(self):
        self.thread.start()
        super().exec()
        self.send_worker.flag_stop = True
        self.thread.quit()
        self.thread.wait()

    def update_progress_bar(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def send_text(self) -> None:
        text = self.plain_text_edit.toPlainText()
        text = text.replace(os.sep, "\n")
        if text.isascii() is False:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Text send only supports ASCII characters\n")
            )
            return
        if self.send_worker.is_sending():
            return
        self.send_worker.send_text_signal.emit(text)

    def send_file(self) -> None:
        if self.file_path is None:
            return
        if os.path.isfile(self.file_path) is False:
            return
        if self.send_worker.is_sending():
            return
        total_bytes = os.path.getsize(self.file_path)
        if total_bytes > 1 * 1024:
            reply = QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Selected file that is too large may take a long time.\n") +
                self.tr("Please confirm to continue.\n"),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
        self.send_worker.send_file_signal.emit(self.file_path)

    def select_file_button_clicked(self) -> None:
        file_path = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), "", "All Files(*.*)"
        )[0]
        if os.path.isfile(file_path):
            # file_size_kb = os.path.getsize(file_path) / 1024
            filename = os.path.basename(file_path)
            if filename.isascii():
                self.file_path = file_path
                self.line_edit_file_path.setText(
                    file_path
                )
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("The file name contains non-ascii characters"),
                )

    def send_button_clicked(self) -> None:
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:
            self.send_text()
        elif current_index == 1:
            self.send_file()
        else:
            pass
        pass

    def stop_button_clicked(self) -> None:
        self.send_worker.flag_stop = True


if __name__ == "__main__":
    pass
