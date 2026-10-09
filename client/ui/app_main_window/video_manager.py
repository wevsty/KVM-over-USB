from __future__ import annotations
import typing
from .app_context import ApplicationContext
from .icon_manager import IconManager
from .mouse_manager import MouseManager
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QImageCapture,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
    QVideoFrame,
    QVideoSink,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QWidget

from PySide6.QtCore import Qt, QObject, QSize
from PySide6.QtGui import QGuiApplication, QSurfaceFormat


class VideoManager:
    """视频管理：设备连接/初始化/截图/录像。

    窗口相关操作统一经 context.window_service 调用，tr 经 context.tr，
    不再直接持有主窗口引用或接收大量窗口绑定方法参数。
    """

    def __init__(
        self,
        context: ApplicationContext,
        *,
        mouse_manager: MouseManager,
        icon_service: IconManager,
        video_widget: QVideoWidget,
        video_disconnect_label: QLabel,
        video_session: VideoSession,
    ):
        # 依赖由组合根注入；窗口行为经 context.window_service 调用
        self._context = context
        self.config = context.config
        self.status = context.status
        self.timer = context.timer
        self.mouse_manager = mouse_manager
        self.icon_service = icon_service
        self.video_widget = video_widget
        self.video_disconnect_label = video_disconnect_label
        self.video_session = video_session

    def init_video_widget(self) -> None:
        # video_widget / video_disconnect_label 由组合根创建后注入，
        # 这里只做配置与装配（避免重建控件导致其他 Manager 持有失效引用）
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._context.window_service.take_central_widget()
        self._context.window_service.set_central_widget(self.video_widget)
        self.video_widget.setMouseTracking(True)
        # self.video_widget.children()[0].setMouseTracking(True)
        for children in self.video_widget.children():
            if isinstance(children, QWidget):
                children.setMouseTracking(True)
        self.video_widget.hide()

        s_format = QSurfaceFormat.defaultFormat()
        s_format.setSwapInterval(0)
        QSurfaceFormat.setDefaultFormat(s_format)

        image_pixmap = self.icon_service.load_pixmap("screen.svg")
        """
        image_pixmap = image_pixmap.scaled(
            128,
            128,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        """
        self.video_disconnect_label.setPixmap(image_pixmap)
        self.video_disconnect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_disconnect_label.setMouseTracking(True)
        self._context.window_service.take_central_widget()
        self._context.window_service.set_central_widget(
            self.video_disconnect_label
        )
        self.video_disconnect_label.show()

    def set_video_widget_enable(self, enable: bool):
        if enable:
            self.video_disconnect_label.hide()
            self.video_widget.show()
            self._context.window_service.take_central_widget()
            self._context.window_service.set_central_widget(self.video_widget)
        else:
            self.video_widget.hide()
            self.video_disconnect_label.show()
            self._context.window_service.take_central_widget()
            self._context.window_service.set_central_widget(
                self.video_disconnect_label
            )

    def video_widget_frame_changed(self, frame: QVideoFrame) -> None:
        self.video_widget.isWindow()
        video_slink = self.video_widget.videoSink()
        video_slink.setVideoFrame(frame)
        self.video_widget.update()
        self.video_widget.repaint()

    def set_aspect_ratio_mode(self) -> None:
        """根据配置切换 video_widget 的宽高比保持模式。
        供 WindowManager.keep_aspect_ratio_toggle 与窗口尺寸调整复用，
        避免其他 Manager 直接持有 video_widget 控件。"""
        if self.status.is_enabled("keep_aspect_ratio"):
            self.video_widget.setAspectRatioMode(
                Qt.AspectRatioMode.KeepAspectRatio
            )
        else:
            self.video_widget.setAspectRatioMode(
                Qt.AspectRatioMode.IgnoreAspectRatio
            )

    def get_mouse_mapping_geometry(
        self,
    ) -> tuple[int, int, int, int, int, int]:
        """返回绝对鼠标映射所需的几何信息 (x_res, y_res, width, height, x_pos, y_pos)。
        未启用摄像头时取自 video_disconnect_label，否则取自 video_widget。
        供 MouseManager 获取坐标，避免其直接持有控件引用。"""
        if not self.status.is_enabled("camera"):
            w = self.video_disconnect_label.width()
            h = self.video_disconnect_label.height()
            return (
                w,
                h,
                w,
                h,
                self.video_disconnect_label.pos().x(),
                self.video_disconnect_label.pos().y(),
            )
        return (
            self.config.video["resolution_x"],
            self.config.video["resolution_y"],
            self.video_widget.width(),
            self.video_widget.height(),
            self.video_widget.pos().x(),
            self.video_widget.pos().y(),
        )

    # 判断屏幕大小是否足够
    @staticmethod
    def is_screen_size_sufficient(
        required_height: int,
        required_width: int,
        screen_height: int,
        screen_width: int,
    ) -> bool:
        if not screen_height >= required_height:
            return False
        if not screen_width >= required_width:
            return False
        return True

    def move_window_to_center(self) -> None:
        qr = self._context.window_service.frame_geometry()
        # 获取中心点
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        # 移动中心点到获取的中心点
        qr.moveCenter(cp)
        # 根据中心点重新计算左上角的坐标
        point = qr.topLeft()
        self._context.window_service.move_window(point)

    def resize_window_with_video_resolution(self) -> None:
        if self.status.is_enabled("fullscreen"):
            return
        menu_bar_height = self._context.window_service.menu_bar().height()
        status_bar_height = self._context.window_service.status_bar().height()
        # 菜单和状态栏附带高度
        additional_height = menu_bar_height + status_bar_height
        # 附带宽度
        additional_width = 0

        # 窗口推荐大小
        recommend_height = self.config.video["resolution_y"] + additional_height
        recommend_width = self.config.video["resolution_x"] + additional_width

        screen_available_size = (
            QGuiApplication.primaryScreen().availableGeometry()
        )
        screen_available_height = screen_available_size.height()
        screen_available_width = screen_available_size.width()
        if self.is_screen_size_sufficient(
            recommend_height,
            recommend_width,
            screen_available_height,
            screen_available_width,
        ):
            # 如果屏幕大小足够
            self._context.window_service.show_normal()
            self._context.window_service.resize_window(
                recommend_width,
                recommend_height,
            )
        else:
            # 如屏幕大小不够则按比例缩小尺寸
            while not (
                self.is_screen_size_sufficient(
                    recommend_height,
                    recommend_width,
                    screen_available_height,
                    screen_available_width,
                )
            ):
                recommend_height = int(recommend_height * 1 / 2)
                recommend_width = int(recommend_width * 1 / 2)
            self._context.window_service.show_normal()
            self._context.window_service.resize_window(
                recommend_width,
                recommend_height,
            )

        # 如果自动居中打开则自动居中窗口
        if self.config.ui["window_auto_to_center"]:
            self.move_window_to_center()
        # 如果自动最大化选项打开则自动最大化窗口
        if self.config.ui["window_auto_maximized"]:
            self._context.window_service.show_maximized()
        # 保持视频比例
        self.set_aspect_ratio_mode()

    def video_device_error_occurred(
        self, error: QCamera.Error, message: str
    ) -> None:
        error_s = (
            f"Device: {self.video_session.device.description()}\n"
            f"Error code: {error}\n"
            f"Message: {message}\n"
        )
        self.disconnect_video_device()
        self._context.window_service.show_critical(
            self._context.tr("Video Device Error"), error_s
        )

    def start_video_device(self) -> None:
        # 使用配置初始化设备
        self.video_session.init_video_device_with_config(self.config.video)
        self.video_session.init_capture_session_with_config(
            self.config.video_record
        )

        camera = self.video_session.camera
        video_sink = self.video_session.video_sink
        # 注册信号
        video_sink.videoFrameChanged.connect(self.video_widget_frame_changed)
        camera.errorOccurred.connect(self.video_device_error_occurred)
        camera.start()

        if not camera.isActive():
            self.status.set_bool("camera", False)
            raise RuntimeError(self._context.tr("Video device start failed"))
        else:
            self.status.set_bool("camera", True)
        self.status.set_bool("video_recording", False)

    def init_video_device(self) -> bool:
        status: bool = False
        try:

            if self.config.video["device"] == "empty_device":
                # 设置为 empty_device 时默认不启用摄像头
                # 此值可作为无采集卡时仅作为输入设备使用
                pass
            else:
                # 使用配置初始化设备
                self.start_video_device()
            status = True
        except RuntimeError as error:
            error_message = str(error)
            self._context.window_service.show_critical(
                self._context.tr("Video initialization error"), error_message
            )
        return status

    def connect_video_device(self) -> None:
        if not self.init_video_device():
            return
        if not self.status.is_enabled("fullscreen"):
            self.resize_window_with_video_resolution()
        if self.status.get_bool("camera"):
            fps = self.video_session.camera.cameraFormat().maxFrameRate()
            self.set_video_widget_enable(True)
            self._context.window_service.set_window_title(
                f"{self._context.window_service.window_title}"
                + " - "
                + f"{self.config.video['resolution_x']}x{self.config.video['resolution_y']}"
                + " @ "
                + f"{fps:.1f}"
            )
        else:
            fps = 60
        self.mouse_manager.update_mouse_report_frequency(int(fps))

    def disconnect_video_device(self) -> None:
        if self.status.is_enabled("camera"):
            self.video_session.camera.stop()
            self.video_session.camera.setActive(False)
            self.status.set_bool("camera", False)
        self.set_video_widget_enable(False)
        self._context.window_service.set_window_title(
            self._context.window_service.window_title
        )


class VideoSession(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.device: QCameraDevice = QCameraDevice()
        self.camera: QCamera = QCamera(self.device)
        self.video_sink: QVideoSink = QVideoSink()
        self.capture_session: QMediaCaptureSession = QMediaCaptureSession()
        self.image_capture: QImageCapture = QImageCapture(self.camera)
        self.video_record: QMediaRecorder = QMediaRecorder(self.camera)

    # 按照视频设备描述返回设备对象
    @staticmethod
    def get_target_video_device(
        device_description: str,
    ) -> QCameraDevice | None:
        cameras: list[QCameraDevice] = QMediaDevices.videoInputs()
        video_device: QCameraDevice | None = None
        for camera in cameras:
            if camera.description() == device_description:
                video_device = camera
                break
        return video_device

    # 根据配置设置相机格式
    def set_camera_format_with_config(
        self, config: dict[str, typing.Any]
    ) -> bool:
        setting_done = False
        for camera_format in self.device.videoFormats():
            resolution_x = camera_format.resolution().width()
            resolution_y = camera_format.resolution().height()
            pixel_format = camera_format.pixelFormat().name.split("_")[1]
            if (
                resolution_x == config["resolution_x"]
                and resolution_y == config["resolution_y"]
                and pixel_format == config["format"]
            ):
                self.camera.setCameraFormat(camera_format)
                setting_done = True
                break
        return setting_done

    # 根据配置初始化视频设备
    def init_video_device_with_config(
        self, config: dict[str, typing.Any]
    ) -> None:
        # 获得设备名
        device_description = config["device"]
        if device_description == "":
            raise RuntimeError(self.tr("Target video device is empty."))
        target_device = self.get_target_video_device(device_description)
        if target_device is None:
            self.device = QCameraDevice()
            raise RuntimeError(self.tr("Target video device not found."))
        else:
            self.device: QCameraDevice = target_device
        # 设置摄像头配置
        self.camera = QCamera(self.device)
        status = self.set_camera_format_with_config(config)
        if not status:
            raise RuntimeError(
                self.tr("Unsupported combination of resolution or format")
            )

    def init_capture_session_with_config(
        self, config: dict[str, typing.Any]
    ) -> None:
        # 设置视频捕捉
        self.capture_session = QMediaCaptureSession()
        self.video_sink = QVideoSink()
        self.image_capture = QImageCapture(self.camera)
        self.video_record = QMediaRecorder(self.camera)

        # capture_session 设定
        self.capture_session.setCamera(self.camera)
        self.capture_session.setVideoSink(self.video_sink)
        self.capture_session.setImageCapture(self.image_capture)
        self.capture_session.setRecorder(self.video_record)

        # image_capture 设定
        self.image_capture.setQuality(QImageCapture.Quality.VeryHighQuality)
        self.image_capture.setFileFormat(QImageCapture.FileFormat.PNG)

        # recorder 设定
        self.video_record.setQuality(QMediaRecorder.Quality[config["quality"]])
        self.video_record.setMediaFormat(QMediaFormat.FileFormat.MPEG4)
        self.video_record.setEncodingMode(
            QMediaRecorder.EncodingMode[config["encoding_mode"]]
        )
        self.video_record.setVideoBitRate(config["encoding_bitrate"])
        self.video_record.setVideoFrameRate(config["frame_rate"])
        self.video_record.setVideoResolution(QSize())
