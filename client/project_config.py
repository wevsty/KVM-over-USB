import os
import typing

import yaml
from loguru import logger

from data.default_config import MAIN_DEFAULT_CONFIG_DATA


class RequiredConfig:
    def __init__(
        self, file_path: str = "config.yaml", data: dict | None = None
    ):
        if data is None:
            data = dict()
        self.file_path: str = file_path
        self.data: dict = data
        if file_path is not None:
            self.load_from_file()

    def load_from_file(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as fp:
                self.data = yaml.safe_load(fp)
        except OSError as err:
            logger.error(f"File open error: {self.file_path}")
            raise RuntimeError(f"File open error: {self.file_path}") from err
        except yaml.YAMLError as err:
            logger.error(f"File parsing error: {self.file_path}")
            raise RuntimeError(f"File parsing error: {self.file_path}") from err

    def save_to_file(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as fp:
            yaml.dump(self.data, fp)

    def config(self) -> dict:
        return self.data


class MainConfig(RequiredConfig):
    def __init__(self, file_path: str = "config.yaml"):
        super().__init__(file_path, None)
        self.root: dict = self.data

        self.connection: dict[str, typing.Any] = dict()
        self.controller: dict[str, typing.Any] = dict()
        self.mouse: dict[str, typing.Any] = dict()
        self.paste_board: dict[str, typing.Any] = dict()
        self.shortcut_keys: dict[str, typing.Any] = dict()
        self.ui: dict[str, typing.Any] = dict()
        self.video: dict[str, typing.Any] = dict()
        self.video_record: dict[str, typing.Any] = dict()
        if file_path is not None:
            self.load_from_file()

    def split_data_node(self):
        self.root: dict = self.data

        self.connection = self.root.get("connection", {})
        self.controller = self.root.get("controller", {})
        self.mouse = self.root.get("mouse", {})
        self.paste_board = self.root.get("paste_board", {})
        self.shortcut_keys = self.root.get("shortcut_keys", {})
        self.ui = self.root.get("ui", {})
        self.video = self.root.get("video", {})
        self.video_record = self.root.get("video_record", {})

    def load_from_file(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as fp:
                fp.write(MAIN_DEFAULT_CONFIG_DATA)
        super().load_from_file()
        self.split_data_node()


if __name__ == "__main__":
    pass
