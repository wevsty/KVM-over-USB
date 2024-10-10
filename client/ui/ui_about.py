import codecs
import sys

from PySide6.QtWidgets import QDialog

from project_path import project_source_directory_path
from ui.ui_resource import about_ui


class AboutDialog(QDialog, about_ui.Ui_AboutDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.label_python_version_value.setText(
            "{}.{}.{}".format(
                sys.version_info.major, sys.version_info.minor, sys.version_info.micro
            )
        )
        self.load_dependencies_info()

    @staticmethod
    def detect_file_bom(path: str) -> tuple[str, int]:
        BOM_TABLE = {
            codecs.BOM_UTF8: "utf-8",
            codecs.BOM_UTF16_LE: "utf-16",
            codecs.BOM_UTF16_BE: "utf-16",
            codecs.BOM_UTF32_LE: "utf-32",
            codecs.BOM_UTF32_BE: "utf-32",
        }
        encoding = "utf-8"
        encoding_length = 0
        with open(path, "rb") as f:
            binary_data = f.read(4)
            for bom, bom_encoding in BOM_TABLE.items():
                if binary_data.startswith(bom):
                    encoding = bom_encoding
                    encoding_length = len(bom)
                    break
        return encoding, encoding_length

    def load_dependencies_info(self):
        data_path = project_source_directory_path("data", "requirements.txt")
        encoding, encoding_length = self.detect_file_bom(data_path)
        # requirements_data = ""
        with open(data_path, "r", encoding=encoding) as fp:
            fp.seek(encoding_length)
            requirements_data = fp.read()
        self.text_edit_info.setText(requirements_data)


if __name__ == "__main__":
    pass
