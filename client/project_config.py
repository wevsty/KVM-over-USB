import yaml
import os
from loguru import logger

import main_default_config


class RequiredConfig:
    def __init__(self, file_path: str):
        self.data: dict = dict()
        self.file_path: str = file_path
        self.create_default_config()
        self.load_from_file()

    def create_default_config(self) -> None:
        pass

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


class MainConfig(RequiredConfig):
    def __init__(self, file_path: str = "config.yaml"):
        super().__init__(file_path)

    def create_default_config(self) -> None:
        if os.path.exists(self.file_path):
            return
        with open(self.file_path, "w", encoding="utf-8") as fp:
            fp.write(main_default_config.DATA)

class DataConfig(RequiredConfig):
    def __init__(self, file_path: str):
        super().__init__(file_path)


if __name__ == '__main__':
    pass
