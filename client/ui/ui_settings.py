import typing

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QComboBox, QDialog

from controller.general_serial import SerialDevice
from ui.ui_resource import settings_ui


class SettingsDialog(QDialog, settings_ui.Ui_SettingsDialog):
    # 选择 combo box 文本为指定预设值
    @staticmethod
    def select_combo_box_preset_as_current_text(
        combo_box_object: QComboBox, text: str
    ) -> bool:
        bret: bool = False
        index = combo_box_object.findText(text)
        if index != -1:
            combo_box_object.setCurrentText(text)
            bret = True
        return bret

    @staticmethod
    def list_video_devices_name() -> list[str]:
        # 获取摄像头信息
        devices = list()
        cameras = QMediaDevices.videoInputs()
        for camera in cameras:
            devices.append(camera.description())
        return devices

    @staticmethod
    def list_video_device_info(device_name: str) -> tuple[list[str], list[str]]:
        resolution_list = list()
        format_list = list()
        cameras = QMediaDevices.videoInputs()
        camera_device = None
        for camera in cameras:
            if camera.description() == device_name:
                camera_device = camera
                break
        if camera_device is None:
            return resolution_list, format_list
        for i in camera_device.videoFormats():
            width = i.resolution().width()
            height = i.resolution().height()
            resolutions_string = f"{width}x{height}"
            if resolutions_string not in resolution_list:
                resolution_list.append(resolutions_string)
            format_string = i.pixelFormat().name.split("_")[1]
            if format_string not in format_list:
                format_list.append(format_string)
        return resolution_list, format_list

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.video_config: dict[str, typing.Any] = dict()
        self.controller_config: dict[str, typing.Any] = dict()
        self.connection_config: dict[str, typing.Any] = dict()
        self.accept_settings: bool = False

        # self.adjustSize()
        # 刷新设备信息
        self.refresh_devices()
        # 注册信号
        self.combo_box_device.currentTextChanged.connect(
            self.refresh_video_device_info
        )
        # self.button_box.accepted.connect(self.accepted)
        # self.button_box.rejected.connect(self.rejected)
        # self.refresh_with_config()

    def accept(self):
        self.accept_settings = True
        super().accept()

    def reject(self):
        self.accept_settings = False
        super().reject()

    # 获取视频配置
    def get_video_config(self) -> dict[str, typing.Any]:
        vc: dict[str, typing.Any] = dict()
        vc["device"] = self.combo_box_device.currentText()
        vc["format"] = self.combo_box_format.currentText()
        resolution = self.combo_box_resolution.currentText()
        x, sep, y = resolution.partition("x")
        try:
            vc["resolution_x"] = int(x)
            vc["resolution_y"] = int(y)
        except ValueError:
            vc["resolution_x"] = 0
            vc["resolution_y"] = 0
        return vc

    # 设置视频配置
    def set_video_config(self, config: dict[str, typing.Any]) -> None:
        self.video_config = config

    # 获取控制器配置
    def get_controller_config(self) -> dict[str, typing.Any]:
        dc: dict[str, typing.Any] = dict()
        dc["type"] = self.combo_box_controller_type.currentText()
        dc["port"] = self.combo_box_com_port.currentText()
        dc["baud_rate"] = int(self.combo_box_baud_rate.currentText())

        if self.is_auto_string(dc["port"]):
            dc["port"] = "auto"
        return dc

    # 设置控制器配置
    def set_controller_config(self, config: dict[str, typing.Any]) -> None:
        self.controller_config = config

    # 获取连接配置
    def get_connection_config(self) -> dict[str, typing.Any]:
        cc: dict[str, typing.Any] = dict()
        if self.check_box_auto_connect.isChecked():
            cc["auto_connect"] = True
        else:
            cc["auto_connect"] = False
        return cc

    # 设置连接配置
    def set_connection_config(self, config: dict[str, typing.Any]) -> None:
        self.connection_config = config

    # 刷新视频选择界面为运行时配置
    def refresh_video_devices_with_config(self) -> None:
        width = self.video_config["resolution_x"]
        height = self.video_config["resolution_y"]
        config_format = self.video_config["format"]
        config_device = self.video_config["device"]
        config_resolution = f"{width}x{height}"

        if config_device == "":
            return
        if self.select_combo_box_preset_as_current_text(
            self.combo_box_device, config_device
        ):
            self.refresh_video_device_info(config_device)
        else:
            return

        # 设定 resolution
        self.select_combo_box_preset_as_current_text(
            self.combo_box_resolution, config_resolution
        )

        # 设定 format
        self.select_combo_box_preset_as_current_text(
            self.combo_box_format, config_format
        )

    # 刷新控制器界面为运行时配置
    def refresh_controller_devices_with_config(self) -> None:
        config_type = self.controller_config["type"]
        config_port = self.controller_config["port"]
        config_baud_rate = str(self.controller_config["baud_rate"])
        self.select_combo_box_preset_as_current_text(
            self.combo_box_controller_type, config_type
        )
        self.select_combo_box_preset_as_current_text(
            self.combo_box_com_port, config_port
        )
        self.select_combo_box_preset_as_current_text(
            self.combo_box_baud_rate, config_baud_rate
        )

    # 刷新连接设置界面为运行时配置
    def refresh_connection_with_config(self) -> None:
        self.check_box_auto_connect.setChecked(
            self.connection_config["auto_connect"]
        )

    # 刷新界面为运行时配置
    def refresh_with_config(self) -> None:
        self.refresh_video_devices_with_config()
        self.refresh_controller_devices_with_config()
        self.refresh_connection_with_config()

    def auto_string(self) -> str:
        return self.tr("auto")

    def is_auto_string(self, value: str) -> bool:
        if self.auto_string().lower() == value.lower():
            return True
        else:
            return False

    # 刷新视频设备列表
    def refresh_video_devices(self):
        self.combo_box_device.clear()
        video_devices = self.list_video_devices_name()
        video_device_name = None
        for device in video_devices:
            self.combo_box_device.addItem(device)
            video_device_name = device
        if video_device_name is not None:
            self.combo_box_device.setCurrentText(video_device_name)
            self.refresh_video_device_info(video_device_name)

    # 刷新视频设备详细信息
    def refresh_video_device_info(self, device_name: str):
        if device_name == "":
            return
        self.combo_box_resolution.clear()
        self.combo_box_format.clear()
        resolution_list, format_list = self.list_video_device_info(device_name)
        default_resolution = None
        default_format = None
        # 设置分辨率combox
        for resolution in resolution_list:
            self.combo_box_resolution.addItem(resolution)
            default_resolution = resolution
        if default_resolution is not None:
            self.combo_box_resolution.setCurrentText(default_resolution)
        # 设置格式combox
        for format_string in format_list:
            self.combo_box_format.addItem(format_string)
            default_format = format_string
        if default_format is not None:
            self.combo_box_format.setCurrentText(default_format)

    # 刷新串行设备
    def refresh_serial_devices(self):
        ports = SerialDevice.list_serial_ports()
        self.combo_box_com_port.clear()
        self.combo_box_com_port.addItem(self.auto_string())
        for port_name in ports:
            self.combo_box_com_port.addItem(port_name)
        self.combo_box_com_port.setCurrentIndex(0)
        self.combo_box_com_port.setCurrentIndex(0)

    # 刷新设备列表
    def refresh_devices(self):
        self.refresh_video_devices()
        self.refresh_serial_devices()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    my_window = SettingsDialog()
    my_window.show()
    app.exec()
    pass
