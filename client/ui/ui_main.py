from PySide6.QtWidgets import QMainWindow

from ui.ui_resource import main_ui


class MainWindow(QMainWindow, main_ui.Ui_main_window):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


if __name__ == "__main__":
    pass
