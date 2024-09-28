import os

import yaml
from loguru import logger

from data.default_config import MAIN_DEFAULT_CONFIG_DATA


class RequiredConfig:
    def __init__(self, file_path: str):
        self.file_path: str = file_path
        self.data: dict = dict()
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
        super().__init__(file_path)

    def load_from_file(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as fp:
                fp.write(MAIN_DEFAULT_CONFIG_DATA)
        super().load_from_file()


if __name__ == '__main__':
    pass
