from __future__ import annotations

import argparse
import ctypes
import os
import platform
import sys
import tempfile

from loguru import logger
from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtWidgets import QApplication

import project_var
from project_path import project_binary_directory_path


def clear_splash():
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(),
            "onefile_%d_splash_feedback.tmp"
            % int(os.environ["NUITKA_ONEFILE_PARENT"]),
        )
        if os.path.exists(splash_filename):
            os.unlink(splash_filename)


def logger_init():
    logger_fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {name} - {message}"
    log_path = project_binary_directory_path("debug.log")
    # 移除logger handler
    logger.remove()

    if project_var.debug_mode:
        if sys.stdout is not None:
            logger.add(sys.stdout, format=logger_fmt, level="DEBUG")
        logger.add(log_path, enqueue=True, level="DEBUG")
        logger.debug("Debug mode enabled")
    else:
        if sys.stdout is not None:
            logger.add(sys.stdout, format=logger_fmt, level="INFO")
    logger.info("Logger initialization completed")


def command_line_parser():
    parser = argparse.ArgumentParser(description="USB KVM Client")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Debug mode (default: disable)",
    )

    args = parser.parse_args()
    # 根据 debug 参数设置 debug 模式
    if not project_var.debug_mode:
        project_var.debug_mode = args.debug
    logger_init()


def os_init():
    system_name = platform.system().lower()
    if system_name == "windows":  # sys.platform == "win32":
        app_id = "open_source_software.usb_kvm_client.gui.1"
        # noinspection PyUnresolvedReferences
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        # 4K分辨率下字体发虚
        # 设置环境变量让渲染使用 freetype
        os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"
        # 设置二进制文件夹为工作目录
        binary_path = project_binary_directory_path()
        os.chdir(binary_path)
    elif system_name == "linux":
        pass
    else:
        pass


def main():
    # 局部导入：app_main_window → window_manager → bootstrap 在模块加载期已
    # 建立，故此处延迟到运行时导入，避免与 AppMainWindow 形成循环依赖
    from .app_main_window import AppMainWindow

    os_init()
    command_line_parser()
    argv = sys.argv
    app = QApplication(argv)

    # 创建翻译器
    app_translator = QTranslator(app)
    qt_base_translator = QTranslator(app)
    # 覆盖窗口类默认的翻译器
    AppMainWindow.QT_BASE_TRANSLATOR = qt_base_translator
    AppMainWindow.WINDOW_TRANSLATOR = app_translator
    # 安装翻译器
    QCoreApplication.installTranslator(AppMainWindow.QT_BASE_TRANSLATOR)
    QCoreApplication.installTranslator(AppMainWindow.WINDOW_TRANSLATOR)

    my_window = AppMainWindow()
    my_window.show()
    # QTimer.singleShot(100, my_window.shortcut_status)
    clear_splash()
    return app.exec()
