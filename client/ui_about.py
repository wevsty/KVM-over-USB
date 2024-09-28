import sys
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import QApplication, QDialog
from project_path import project_source_directory_path
from ui import about_ui


class AboutDialog(QDialog, about_ui.Ui_AboutDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.label_python_version_value.setText(
            "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
        )
        self.load_requirements_file()

    def load_requirements_file(self):
        requirements_path = project_source_directory_path("data", "requirements.txt")
        # requirements_data = ""
        with open(requirements_path, "r", encoding="utf-16") as fp:
            requirements_data = fp.read()
        self.text_edit_info.setText(requirements_data)


if __name__ == "__main__":
    pass
