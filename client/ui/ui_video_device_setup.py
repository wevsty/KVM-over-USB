from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QDialog

from ui.ui_resource import video_device_setup_ui


@dataclass
class VideoDeviceConfig:
    auto_connect: bool = False
    device: str = ""
    format: str = ""
    resolution_x: int = 0
    resolution_y: int = 0

    def from_dict(self, data: dict) -> None:
        self.auto_connect = data.get("auto_connect", False)
        self.device = data.get("device", "")
        self.format = data.get("format", "")
        self.resolution_x = data.get("resolution_x", 0)
        self.resolution_y = data.get("resolution_y", 0)

    def to_dict(self) -> dict:
        data = {
            "auto_connect": self.auto_connect,
            "device": self.device,
            "format": self.format,
            "resolution_x": self.resolution_x,
            "resolution_y": self.resolution_y,
        }
        return data


@dataclass
class AudioDeviceConfig:
    audio_support: bool = False
    audio_device_in: str = ""
    audio_device_out: str = ""

    def from_dict(self, data: dict) -> None:
        self.audio_support = data.get("audio_support", False)
        self.audio_device_in = data.get("audio_device_in", "")
        self.audio_device_out = data.get("audio_device_out", "")

    def to_dict(self) -> dict:
        data = {
            "audio_support": self.audio_support,
            "audio_device_in": self.audio_device_in,
            "audio_device_out": self.audio_device_out,
        }
        return data


class VideoDeviceSetupDialog(QDialog, video_device_setup_ui.Ui_dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.reference_video_config = VideoDeviceConfig()
        self.reference_audio_config = AudioDeviceConfig()
        self.refresh_devices()
        self.adjustSize()
        self.combo_box_device.currentTextChanged.connect(
            self.refresh_video_device_info
        )

    def get_auto_string(self) -> str:
        return self.tr("auto")

    def is_auto_string(self, value: str) -> bool:
        if self.get_auto_string() == value:
            return True
        else:
            return False

    def get_video_config(self) -> VideoDeviceConfig:
        vc = VideoDeviceConfig()
        vc.device = self.combo_box_device.currentText()
        vc.format = self.combo_box_format.currentText()
        resolution = self.combo_box_resolution.currentText()
        x, sep, y = resolution.partition("x")
        try:
            vc.resolution_x = int(x)
            vc.resolution_y = int(y)
        except ValueError:
            vc.resolution_x = 0
            vc.resolution_y = 0
        if self.check_box_auto_connect.isChecked():
            vc.auto_connect = True
        else:
            vc.auto_connect = False
        return vc

    def get_audio_config(self) -> AudioDeviceConfig:
        ac = AudioDeviceConfig()
        ac.audio_device_in = self.combo_box_audio_in.currentText()
        ac.audio_device_out = self.combo_box_audio_out.currentText()
        if self.check_box_audio_support.isChecked():
            ac.audio_support = True
        else:
            ac.audio_support = False
        return ac

    def set_video_config(self, config: VideoDeviceConfig) -> None:
        self.reference_video_config = config

    def set_audio_config(self, config: AudioDeviceConfig) -> None:
        self.reference_audio_config = config

    def select_video_devices_with_config(self) -> None:
        video_devices = self.list_video_devices_name()
        reference_width = self.reference_video_config.resolution_x
        reference_height = self.reference_video_config.resolution_y
        reference_resolution = f"{reference_width}x{reference_height}"

        select_device_name = None
        for device_name in video_devices:
            if device_name == self.reference_video_config.device:
                select_device_name = device_name
                self.combo_box_device.setCurrentText(select_device_name)
        if select_device_name is None:
            pass
        else:
            self.refresh_video_device_info(select_device_name)

        find_result = self.combo_box_resolution.findText(reference_resolution)
        if find_result != -1:
            self.combo_box_resolution.setCurrentText(reference_resolution)
        find_result = self.combo_box_format.findText(
            self.reference_video_config.format
        )
        if find_result != -1:
            self.combo_box_format.setCurrentText(
                self.reference_video_config.format
            )
        return

    def select_audio_devices_with_config(self) -> None:
        selected_audio_device_in = self.reference_audio_config.audio_device_in
        selected_audio_device_out = self.reference_audio_config.audio_device_out
        find_result = self.combo_box_audio_in.findText(selected_audio_device_in)
        if find_result != -1:
            self.combo_box_audio_in.setCurrentText(selected_audio_device_in)
        find_result = self.combo_box_audio_out.findText(
            selected_audio_device_out
        )
        if find_result != -1:
            self.combo_box_audio_out.setCurrentText(selected_audio_device_out)

    @staticmethod
    def list_video_devices_name() -> list[str]:
        # 获取摄像头信息
        devices = list()
        cameras = QMediaDevices.videoInputs()
        for camera in cameras:
            # self.combo_box_device.addItem(camera.description())
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

    # 刷新设备列表
    def refresh_devices(self):
        self.refresh_video_devices()
        self.refresh_audio_device()

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

    # 刷新音频设备列表
    def refresh_audio_device(self):
        self.combo_box_audio_in.clear()
        self.combo_box_audio_out.clear()
        self.combo_box_audio_in.addItem(self.get_auto_string())
        self.combo_box_audio_out.addItem(self.get_auto_string())
        self.combo_box_audio_in.setCurrentText(self.get_auto_string())
        self.combo_box_audio_out.setCurrentText(self.get_auto_string())

        audio_in_devices = QMediaDevices.audioInputs()
        audio_out_devices = QMediaDevices.audioOutputs()

        for device in audio_in_devices:
            description = device.description()
            self.combo_box_audio_in.addItem(description)

        for device in audio_out_devices:
            description = device.description()
            self.combo_box_audio_out.addItem(description)


if __name__ == "__main__":
    pass
