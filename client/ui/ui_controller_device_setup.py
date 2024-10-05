from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDialog

from controller_device import ControllerDevice
from ui.ui_resource import controller_device_setup_ui


@dataclass
class ControllerDeviceConfig:
    port: str = "auto"
    baud: int = ""

    def from_dict(self, data: dict) -> None:
        self.port = data.get("port", "auto")
        self.baud = data.get("baud", 9600)

    def to_dict(self) -> dict:
        data = {
            "port": self.port,
            "baud": self.baud,
        }
        return data


class ControllerDeviceSetupDialog(QDialog, controller_device_setup_ui.Ui_ControllerDeviceSetupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.line_edit_baud.setValidator(QIntValidator())

    def set_controller_device_config(self, data: ControllerDeviceConfig) -> None:
        port_name_list = ControllerDevice.detect_serial_ports()
        self.combobox_com_port.clear()
        self.combobox_com_port.addItem(self.tr("auto"))
        for port_name in port_name_list:
            self.combobox_com_port.addItem(port_name)
        self.combobox_com_port.setCurrentIndex(0)
        self.line_edit_baud.setText(str(data.baud))

    def get_controller_device_config(self) -> ControllerDeviceConfig:
        config = ControllerDeviceConfig()
        config.port = self.combobox_com_port.currentText()
        if config.port == self.tr("auto"):
            config.port = "auto"
        config.baud = int(self.line_edit_baud.text())
        return config


if __name__ == "__main__":
    pass
