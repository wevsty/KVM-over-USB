from __future__ import annotations
from loguru import logger
import sys
import typing
from .app_context import ApplicationContext
from PySide6.QtCore import QTranslator

import os
from PySide6.QtCore import QLocale
from project_config import MainConfig
from project_info import CONFIG_VERSION_STRING
from project_path import (
    project_binary_directory_path,
    project_source_directory_path,
)


class ConfigManager:
    """配置管理：加载/保存/语言/调试"""

    def __init__(
        self,
        context: ApplicationContext,
        *,
        qt_base_translator: QTranslator,
        window_translator: QTranslator,
        child_dialog: list[typing.Any],
        retranslate_ui: typing.Callable[[], None],
    ):
        # 依赖全部由组合根（AppMainWindow）显式注入，不再持有主窗口引用
        # tr / show_critical 经 context 共享，减少构造参数
        self._context = context
        self.QT_BASE_TRANSLATOR = qt_base_translator
        self.WINDOW_TRANSLATOR = window_translator
        self.child_dialog = child_dialog
        self.tr = context.tr
        self.retranslate_ui = retranslate_ui
        self.show_critical = context.window_service.show_critical

    @property
    def config(self) -> MainConfig | None:
        """当前配置对象由 ApplicationContext 持有（组合根在加载后写入）"""
        return self._context.config

    def load_config(self) -> None:
        try:
            self._context.config = MainConfig(
                project_binary_directory_path("config.yaml")
            )
            config_version = self.config.root["config_version"]
            if config_version != CONFIG_VERSION_STRING:
                raise ValueError(
                    self.tr(
                        "The configuration file does not match the program.\n"
                    )
                    + self.tr(
                        "Please delete the existing configuration file.\n"
                    )
                )
        except Exception as err:
            self.show_critical(
                self.tr("Error"),
                self.tr("Import config error:\n{}\n").format(err),
            )
            sys.exit(1)

    def save_config(self) -> None:
        # 保存配置文件
        self.config.save_to_file()

    def to_enabled_string(self, value: bool) -> str:
        if value:
            return self.tr("Enable")
        else:
            return self.tr("Disable")

    def select_language_name(self) -> str:
        config_language: str = self.config.ui["language"].lower()
        # 获取系统当前区域设置
        sys_locale = QLocale.system()
        # 获取完整的语言环境名称
        # 如 zh_cn en_us
        sys_locale_name = sys_locale.name().lower()
        if config_language == "auto":
            ui_locale_name = sys_locale_name
        elif config_language.startswith("english"):
            ui_locale_name = "en_us"
        elif config_language.startswith("simplified chinese"):
            ui_locale_name = "zh_cn"
        elif config_language.startswith("traditional chinese"):
            ui_locale_name = "zh_tw"
        else:
            ui_locale_name = "en_us"
        return ui_locale_name

    def refresh_translate(self):
        qt_base_translator = self.QT_BASE_TRANSLATOR
        window_translator = self.WINDOW_TRANSLATOR

        selected_language: str = self.select_language_name()
        translation_directory_path = project_source_directory_path(
            "translations"
        )
        translation_files_path: list[typing.Tuple[str, QTranslator]] = [
            (
                os.path.join(
                    translation_directory_path, f"qtbase_{selected_language}.qm"
                ),
                qt_base_translator,
            ),
            (
                os.path.join(
                    translation_directory_path, f"main_{selected_language}.qm"
                ),
                window_translator,
            ),
        ]

        # 清空翻译
        qt_base_translator.load("")
        window_translator.load("")

        # 载入翻译
        for file_path, translator in translation_files_path:
            if os.path.isfile(file_path):
                translator.load(file_path)

        # 更新UI（retranslate_ui 已在注入时绑定主窗口，无需再传窗口）
        self.retranslate_ui()
        for child in self.child_dialog:
            if hasattr(child, "retranslateUi"):
                child.retranslateUi(child)
            else:
                logger.error("Unknown object type.")
