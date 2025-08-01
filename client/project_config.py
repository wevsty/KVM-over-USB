import os

import yaml
from loguru import logger

from data.default_config import MAIN_DEFAULT_CONFIG_DATA


class RequiredConfig:
    def __init__(self, file_path: str | None = None, data: dict | None = None):
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

        self.connection: dict | None = None
        self.controller: dict | None = None
        self.mouse: dict | None = None
        self.paste_board: dict | None = None
        self.shortcut_keys: dict | None = None
        self.ui: dict | None = None
        self.video: dict | None = None
        self.video_record: dict | None = None
        if file_path is not None:
            self.load_from_file()

    def split_data_node(self):
        self.root: dict = self.data

        self.connection = self.root.get("connection", None)
        self.controller = self.root.get("controller", None)
        self.mouse = self.root.get("mouse", None)
        self.paste_board = self.root.get("paste_board", None)
        self.shortcut_keys = self.root.get("shortcut_keys", None)
        self.ui = self.root.get("ui", None)
        self.video = self.root.get("video", None)
        self.video_record = self.root.get("video_record", None)

    def load_from_file(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as fp:
                fp.write(MAIN_DEFAULT_CONFIG_DATA)
        super().load_from_file()
        self.split_data_node()


if __name__ == "__main__":
    pass
